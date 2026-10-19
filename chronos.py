#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chronos — Organizador de Fotos por Data (Nautilus Script) v5.5
Formato: AAAAMMDD_Evento-Local
Histórico ComboBox (texto cru) + Sanitização Inteligente (hífens preservados)
Interface GTK3 nativa, tema dark herdado, PyGObject.

Mudanças v5.5:
  - Seletor de pasta de destino via Gtk.FileChooserDialog (substitui "um nível acima")
  - Pasta inicial do filechooser: /home/$USER/Imagens (criada se não existir)
  - Persistência da última pasta escolhida no histórico JSON
  - Pré-seleção automática da última pasta na próxima execução

Mudanças v5.4:
  - Extração EXIF fiável para RAWs via exifread (fallback)
  - Corrigido filtro de URIs file:// do Nautilus
  - Removida tag EXIF 306 (DateTime = data de modificação, não de captura)
  - Sanitização substitui underscores por hífens (separador consistente)
  - Escrita atómica do histórico JSON (os.replace)
  - Refactor: getexif() directo (Pillow 10+), _getexif removido
"""

import sys, os, shutil, datetime, urllib.parse, re, io, json
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf
from PIL import Image

# Pango é importado separadamente — não está acessível via Gtk.Pango
try:
    gi.require_version('Pango', '1.0')
    from gi.repository import Pango
    HAS_PANGO = True
except (ImportError, ValueError):
    HAS_PANGO = False

# exifread é opcional — fallback para RAWs quando Pillow não extrai EXIF
try:
    import exifread
    HAS_EXIFREAD = True
except ImportError:
    HAS_EXIFREAD = False

os.environ.setdefault("GTK_THEME", "Adwaita:dark")

# ─────────────────────────────────────────────────────────────────────────────
# 1. CONFIGURAÇÃO & HISTÓRICO
# ─────────────────────────────────────────────────────────────────────────────
HISTORY_DIR = os.path.expanduser("~/.config/organizar_fotos")
HISTORY_FILE = os.path.join(HISTORY_DIR, "historico.json")

IMAGE_EXTS = {
    '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.webp', '.bmp', '.gif',
    '.cr2', '.cr3', '.nef', '.arw', '.dng', '.orf', '.rw2', '.pef', '.srw',
    '.raf', '.3fr', '.iiq', '.kdc', '.mos', '.mef', '.nrw', '.ptx', '.r3d',
    '.rwl', '.sr2', '.srf', '.gpr', '.erf'
}
SIDECAR_EXTS = ('.xmp', '.pp3', '.dop')

# Tags EXIF tentadas por ordem de prioridade:
# 36867 = DateTimeOriginal (data real de captura)
# 36868 = DateTimeDigitized (data de digitalização)
# NOTA: tag 306 (DateTime) removida — é data de modificação do ficheiro,
#       não de captura. Causava datas erradas em fotos pós-processadas.
EXIF_TAGS_PRIORIDADE = (36867, 36868)


def load_history():
    try:
        if os.path.isfile(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return (data.get("eventos", []),
                        data.get("locais", []),
                        data.get("ultima_pasta"))
    except Exception:
        pass
    return [], [], None


def save_history(eventos, locais, ultima_pasta=None):
    """Escrita atómica: grava em .tmp e faz os.replace() — evita corrupção
    se o processo for interrompido a meio do json.dump.
    `ultima_pasta` (opcional) persiste a pasta de destino escolhida pelo
    utilizador para re-aparecer pré-selecionada na próxima execução."""
    os.makedirs(HISTORY_DIR, exist_ok=True)
    data = {
        "eventos": sorted(set(eventos)),
        "locais": sorted(set(locais)),
    }
    if ultima_pasta:
        data["ultima_pasta"] = ultima_pasta
    tmp = HISTORY_FILE + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, HISTORY_FILE)  # atómico em POSIX


# ─────────────────────────────────────────────────────────────────────────────
# 2. EXTRAÇÃO EXIF & SIDECARS
# ─────────────────────────────────────────────────────────────────────────────
def _parse_exif_date(dt_str):
    """Tenta interpretar string EXIF em vários formatos possíveis.
    Cobre: 'YYYY:MM:DD HH:MM:SS', 'YYYY:MM:DD HH:MM', 'YYYY:MM:DD',
    'YYYY-MM-DD HH:MM:SS' (algumas câmaras usam hífen), e variantes com T."""
    if not dt_str:
        return None
    # Aceitar bytes ou str
    if isinstance(dt_str, bytes):
        s = dt_str.decode('utf-8', errors='ignore')
    else:
        s = str(dt_str)
    s = s.strip().strip('\x00').strip()
    if not s:
        return None

    # Lista de formatos a tentar (ordem = prioridade)
    formatos = [
        "%Y:%m:%d %H:%M:%S",   # Padrão EXIF: 2024:01:15 14:30:00
        "%Y:%m:%d %H:%M",       # Sem segundos
        "%Y:%m:%d",             # Apenas data
        "%Y-%m-%d %H:%M:%S",   # Hífen em vez de cólon (Sony, algumas Samsung)
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",   # Barras (alguns smartphones)
        "%Y/%m/%d",
    ]
    for fmt in formatos:
        try:
            # Truncar ao comprimento esperado do formato para evitar erros
            # com chars extra no fim (ex.: timezone)
            expected_len = len(fmt.replace('%Y', '2024').replace('%m', '01').replace('%d', '15')
                                        .replace('%H', '14').replace('%M', '30').replace('%S', '00'))
            return datetime.datetime.strptime(s[:expected_len], fmt)
        except ValueError:
            continue

    # Última tentativa: extrair apenas YYYY:MM:DD ou YYYY-MM-DD (primeiros 10 chars)
    for fmt in ("%Y:%m:%d", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(s[:10], fmt)
        except ValueError:
            continue
    return None


def _exif_from_pillow(caminho):
    """Extrai data de captura via Pillow (funciona para JPEG/PNG/TIFF/WebP).
    Retorna datetime ou None se não conseguir."""
    try:
        with Image.open(caminho) as img:
            exif = img.getexif() if hasattr(img, 'getexif') else None
            if not exif:
                return None
            for tag_id in EXIF_TAGS_PRIORIDADE:
                val = exif.get(tag_id)
                if val:
                    dt = _parse_exif_date(val)
                    if dt:
                        return dt
                    # Se a tag existe mas o parsing falhou, continua para a próxima tag
    except Exception:
        return None
    return None


def _exif_from_exifread(caminho):
    """Extrai data de captura via exifread — funciona com RAWs que o Pillow
    não consegue abrir. Lê apenas os bytes necessários, não decodifica pixels."""
    if not HAS_EXIFREAD:
        return None
    try:
        with open(caminho, 'rb') as f:
            tags = exifread.process_file(f, details=False,
                                          stop_tag='EXIF DateTimeOriginal')
        for key in ('EXIF DateTimeOriginal', 'EXIF DateTimeDigitized', 'Image DateTime'):
            val = tags.get(key)
            if val:
                dt = _parse_exif_date(str(val))
                if dt:
                    return dt
    except Exception:
        pass
    return None


def _exif_from_exiftool(caminho):
    """Fallback final: chama o binário 'exiftool' externo.
    É o método mais robusto para JPEGs com EXIF não-padrão (Samsung, iPhone,
    câmaras antigas). Requer exiftool instalado no sistema."""
    import subprocess
    try:
        # -s3 = short output (apenas valores), -n = formato numérico
        # Tenta DateTimeOriginal primeiro, depois DateTimeDigitized
        result = subprocess.run(
            ['exiftool', '-s3', '-DateTimeOriginal', '-DateTimeDigitized', caminho],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if not line:
                    continue
                dt = _parse_exif_date(line)
                if dt:
                    return dt
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    return None


def obter_data_exif(caminho):
    """Retorna (datetime, used_fallback_mtime, fonte).
    Estratégia:
      1. Pillow.getexif() — rápido, funciona para formatos raster comuns
      2. exifread — lê EXIF bruto, funciona para a maioria dos RAWs
      3. exiftool (subprocess) — mais robusto, fallback final para EXIF exótico
      4. os.path.getmtime() — último recurso (sinaliza com used_fallback=True)
    `fonte` é uma string curta para diagnóstico: 'pillow', 'exifread',
    'exiftool', ou 'mtime'.
    """
    # 1. Pillow
    dt = _exif_from_pillow(caminho)
    if dt:
        return dt, False, 'pillow'

    # 2. exifread (RAWs e fallback geral)
    dt = _exif_from_exifread(caminho)
    if dt:
        return dt, False, 'exifread'

    # 3. exiftool (subprocess) — mais robusto, pega qualquer EXIF
    dt = _exif_from_exiftool(caminho)
    if dt:
        return dt, False, 'exiftool'

    # 4. mtime (último recurso)
    return datetime.datetime.fromtimestamp(os.path.getmtime(caminho)), True, 'mtime'


def get_sidecars(main_file):
    """Retorna sidecars existentes para o ficheiro principal.
    Cobertura dos padrões:
      - ficheiro.xmp        (Darktable, Lightroom)
      - ficheiro.jpg.xmp    (Adobe Camera Raw, DxO)
    """
    src_dir = os.path.dirname(main_file)
    stem = os.path.splitext(os.path.basename(main_file))[0]
    ext = os.path.splitext(os.path.basename(main_file))[1]
    candidates = set()
    for sc_ext in SIDECAR_EXTS:
        candidates.add(os.path.join(src_dir, f"{stem}{sc_ext}"))
        candidates.add(os.path.join(src_dir, f"{stem}{ext}{sc_ext}"))
    return [c for c in candidates if os.path.isfile(c)]


# ─────────────────────────────────────────────────────────────────────────────
# 3. UTILITÁRIOS (Sanitização Inteligente)
# ─────────────────────────────────────────────────────────────────────────────
def sanitize(text):
    """Normaliza texto para uso em nome de pasta.
    - Substitui espaços E underscores por hífens (separador consistente)
    - Preserva hífens existentes (Trás-os-Montes -> Trás-os-Montes)
    - Mantém acentos e caracteres Unicode (alnum)
    - Remove caracteres inválidos (símbolos, pontuação)
    - Colapsa hífens repetidos
    - Remove hífens no início/fim
    """
    if text is None:
        return None
    t = text.strip()

    # 1. Espaços → hífens
    t = t.replace(' ', '-')

    # 2. Underscores → hífens (evita "20240101_Festa_Casa_Local" com 2 underscores)
    t = t.replace('_', '-')

    # 3. Remove tudo o que não for \w (Unicode) ou hífen
    #    \w em Python 3 str já inclui acentos; flag re.UNICODE é redundante mas documentativa
    t = re.sub(r'[^\w-]', '', t, flags=re.UNICODE)

    # 4. Colapsa hífens repetidos ("A--B" -> "A-B")
    t = re.sub(r'-+', '-', t)

    # 5. Remove hífens nas pontas
    return t.strip('-') or "Indefinido"


def image_to_pixbuf(filepath, max_size=280):
    """Gera thumbnail GdkPixbuf a partir de qualquer formato que o Pillow suporte.
    Para RAWs, o Pillow usa o plugin rawpy/tifffile se disponível — caso contrário
    retorna None e o diálogo mostra ícone genérico."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in IMAGE_EXTS:
        return None
    try:
        with Image.open(filepath) as img:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            loader = GdkPixbuf.PixbufLoader.new()
            loader.write(buffer.getvalue())
            loader.close()
            return loader.get_pixbuf()
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 4. DIÁLOGOS GTK3
# ─────────────────────────────────────────────────────────────────────────────
def janela_principal(ultima_pasta=None):
    """Diálogo inicial de configuração.
    Retorna (ask_mode, pasta_destino) ou (None, None) se cancelado.
    `ultima_pasta` (opcional) pré-preenche o campo de destino — usado para
    persistir a última escolha entre execuções."""
    win = Gtk.Dialog(title="Chronos — Organizar Fotos por Data", default_width=480)
    win.set_resizable(False)
    win.set_position(Gtk.WindowPosition.CENTER)
    win.set_border_width(20)
    win.set_modal(True)
    box = win.get_content_area()
    box.set_spacing(15)

    lbl = Gtk.Label(label="Agrupar fotos por data de captura.\nConfigure as opções:")
    lbl.set_xalign(0); lbl.set_line_wrap(True)
    box.pack_start(lbl, False, False, 0)

    check_ask = Gtk.CheckButton(label="Pedir Evento e Local para cada data")
    check_ask.set_active(True)
    box.pack_start(check_ask, False, False, 8)

    # ── Seletor de pasta de destino ────────────────────────────────────────
    # Substitui o antigo "Criar pasta(s) um nível acima" — agora o utilizador
    # escolhe explicitamente onde as pastas serão criadas, com navegação real.
    frame_dest = Gtk.Frame(label="Pasta de destino")
    frame_dest.set_label_align(0.5, 0.5)
    box_dest = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    box_dest.set_border_width(8)

    # Label que mostra o caminho escolhido (pré-preenchido se houver histórico)
    default_pasta = ultima_pasta or os.path.expanduser("~/Imagens")
    lbl_pasta = Gtk.Label(label=default_pasta)
    lbl_pasta.set_xalign(0)
    lbl_pasta.set_halign(Gtk.Align.FILL)
    # Ellipsize para caminhos longos (Pango pode não estar disponível em todos os sistemas)
    if HAS_PANGO:
        lbl_pasta.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        lbl_pasta.set_max_width_chars(40)
    lbl_pasta.set_selectable(True)
    # Estado: guarda o caminho actual num dicionário mutável (closure-friendly)
    estado = {"pasta": default_pasta}

    btn_browse = Gtk.Button(label="Procurar...")
    btn_browse.get_style_context().add_class(Gtk.STYLE_CLASS_SUGGESTED_ACTION)

    def abrir_filechooser(_):
        # Pasta inicial: ~/Imagens (criada se não existir), ou a última usada
        pasta_inicial = estado["pasta"] or os.path.expanduser("~/Imagens")
        # Garantir que ~/Imagens existe para o filechooser não saltar para /
        if not os.path.isdir(pasta_inicial):
            try:
                os.makedirs(pasta_inicial, exist_ok=True)
            except OSError:
                pasta_inicial = os.path.expanduser("~")

        dlg = Gtk.FileChooserDialog(
            title="Escolher pasta de destino",
            parent=win,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dlg.add_buttons(
            "Cancelar", Gtk.ResponseType.CANCEL,
            "Selecionar", Gtk.ResponseType.OK,
        )
        dlg.set_current_folder(pasta_inicial)
        dlg.set_modal(True)

        # Botão OK com estilo sugerido
        btn_ok_fc = dlg.get_widget_for_response(Gtk.ResponseType.OK)
        if btn_ok_fc:
            btn_ok_fc.get_style_context().add_class(Gtk.STYLE_CLASS_SUGGESTED_ACTION)

        res = dlg.run()
        if res == Gtk.ResponseType.OK:
            nova_pasta = dlg.get_filename()
            estado["pasta"] = nova_pasta
            lbl_pasta.set_label(nova_pasta)
        dlg.destroy()

    btn_browse.connect("clicked", abrir_filechooser)

    box_dest.pack_start(lbl_pasta, True, True, 0)
    box_dest.pack_end(btn_browse, False, False, 0)
    frame_dest.add(box_dest)
    box.pack_start(frame_dest, False, False, 8)

    win.add_button("Cancelar", Gtk.ResponseType.CANCEL)
    btn = win.add_button("Iniciar", Gtk.ResponseType.OK)
    btn.get_style_context().add_class(Gtk.STYLE_CLASS_SUGGESTED_ACTION)
    win.show_all()
    res = win.run()
    win.destroy()

    if res == Gtk.ResponseType.OK:
        return check_ask.get_active(), estado["pasta"]
    return None, None


def janela_por_data(data_str, caminho_foto, hist_ev, hist_loc):
    dlg = Gtk.Dialog(title=f"📅 {data_str}", default_width=420)
    dlg.set_position(Gtk.WindowPosition.CENTER)
    dlg.set_border_width(20)
    dlg.set_resizable(False)
    dlg.set_modal(True)
    box = dlg.get_content_area()
    box.set_spacing(15)

    pixbuf = image_to_pixbuf(caminho_foto)
    img = Gtk.Image.new_from_pixbuf(pixbuf) if pixbuf else Gtk.Image.new_from_icon_name(
        "image-x-generic-symbolic", Gtk.IconSize.DIALOG)
    box.pack_start(img, True, True, 10)

    grid = Gtk.Grid()
    grid.set_row_spacing(10)
    grid.set_column_spacing(10)
    grid.set_halign(Gtk.Align.CENTER)

    combo_ev = Gtk.ComboBoxText.new_with_entry()
    for ev in hist_ev:
        combo_ev.append_text(ev)
    # set_entry_text_column(0) é o default — chamada omitida

    combo_loc = Gtk.ComboBoxText.new_with_entry()
    for loc in hist_loc:
        combo_loc.append_text(loc)

    lbl_ev = Gtk.Label(label="Evento:"); lbl_ev.set_xalign(1)
    lbl_loc = Gtk.Label(label="Local:"); lbl_loc.set_xalign(1)

    grid.attach(lbl_ev, 0, 0, 1, 1); grid.attach(combo_ev, 1, 0, 1, 1)
    grid.attach(lbl_loc, 0, 1, 1, 1); grid.attach(combo_loc, 1, 1, 1, 1)
    box.pack_start(grid, False, False, 0)

    btn_ok = dlg.add_button("OK", Gtk.ResponseType.OK)
    dlg.add_button("Cancelar", Gtk.ResponseType.CANCEL)
    btn_ok.get_style_context().add_class(Gtk.STYLE_CLASS_SUGGESTED_ACTION)
    btn_ok.set_sensitive(False)

    def validar(*args):
        ev = (combo_ev.get_active_text() or "").strip()
        loc = (combo_loc.get_active_text() or "").strip()
        btn_ok.set_sensitive(bool(ev) and bool(loc))

    combo_ev.get_child().connect("changed", validar)
    combo_loc.get_child().connect("changed", validar)

    dlg.show_all()
    res = dlg.run()
    ev = (combo_ev.get_active_text() or "").strip()
    loc = (combo_loc.get_active_text() or "").strip()
    dlg.destroy()

    return (ev, loc) if res == Gtk.ResponseType.OK else None


# ─────────────────────────────────────────────────────────────────────────────
# 5. LÓGICA PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────
def _normalizar_uri(u):
    """Converte URI do Nautilus (file://) ou path relativo em path absoluto.
    Tem de ser chamado ANTES de os.path.isfile() — caso contrário URIs file://
    são filtrados pelo isfile() e nunca chegam à lista de ficheiros."""
    if u.startswith("file://"):
        return urllib.parse.unquote(u[7:])
    return os.path.abspath(u)


def _diagnostico_exif(caminho):
    """Diagnóstico detalhado para um ficheiro: mostra EXIF bruto, fontes
    tentadas e resultado. Usado em modo --debug."""
    print(f"\n── {os.path.basename(caminho)} ──")
    print(f"   Caminho: {caminho}")

    # 1. Pillow
    try:
        with Image.open(caminho) as img:
            pillow_exif = img.getexif() if hasattr(img, 'getexif') else None
            print(f"   Pillow: getexif()={'OK' if pillow_exif else 'VAZIO/NONE'}")
            if pillow_exif:
                # Mostrar as 3 tags relevantes
                for tid, name in [(36867, 'DateTimeOriginal'),
                                  (36868, 'DateTimeDigitized'),
                                  (306, 'DateTime')]:
                    val = pillow_exif.get(tid)
                    print(f"      Tag {tid} ({name}): {val!r}")
    except Exception as e:
        print(f"   Pillow: EXCEÇÃO — {type(e).__name__}: {e}")

    # 2. exifread
    if HAS_EXIFREAD:
        try:
            with open(caminho, 'rb') as f:
                tags = exifread.process_file(f, details=False,
                                              stop_tag='EXIF DateTimeOriginal')
            dt_orig = tags.get('EXIF DateTimeOriginal')
            dt_dig = tags.get('EXIF DateTimeDigitized')
            dt_img = tags.get('Image DateTime')
            print(f"   exifread: DateTimeOriginal={dt_orig!r}, "
                  f"Digitized={dt_dig!r}, Image={dt_img!r}")
        except Exception as e:
            print(f"   exifread: EXCEÇÃO — {type(e).__name__}: {e}")
    else:
        print(f"   exifread: NÃO INSTALADO (pip install exifread)")

    # 3. exiftool (subprocess)
    import shutil as _sh
    if _sh.which('exiftool'):
        try:
            import subprocess
            result = subprocess.run(
                ['exiftool', '-s3', '-DateTimeOriginal', '-DateTimeDigitized', caminho],
                capture_output=True, text=True, timeout=10
            )
            print(f"   exiftool: returncode={result.returncode}, stdout={result.stdout.strip()!r}")
        except Exception as e:
            print(f"   exiftool: EXCEÇÃO — {type(e).__name__}: {e}")
    else:
        print(f"   exiftool: NÃO INSTALADO (sudo apt install libimage-exiftool-perl)")

    # 4. Resultado final
    dt, used_fb, fonte = obter_data_exif(caminho)
    print(f"   → Resultado: {dt.strftime('%Y-%m-%d %H:%M:%S')} (fonte={fonte}, "
          f"fallback_mtime={used_fb})")


def main():
    # Processar flag --debug ANTES do resto
    debug_mode = '--debug' in sys.argv
    if debug_mode:
        sys.argv.remove('--debug')
        print("🔍 MODO DEBUG ativado — informação detalhada por ficheiro")

    # 1. Normalizar URIs e filtrar ficheiros existentes
    ficheiros = []
    for u in sys.argv[1:]:
        path = _normalizar_uri(u)
        if os.path.isfile(path):
            ficheiros.append(path)

    if not ficheiros:
        dlg = Gtk.MessageDialog(text="Nenhuma foto válida selecionada.", type=Gtk.MessageType.ERROR)
        dlg.add_buttons("OK", Gtk.ResponseType.OK)
        dlg.run(); dlg.destroy()
        return

    # 2. Filtrar apenas imagens/RAWs suportados
    principais = [f for f in ficheiros if os.path.splitext(f)[1].lower() in IMAGE_EXTS]
    if not principais:
        dlg = Gtk.MessageDialog(text="Nenhum ficheiro de imagem/RAW selecionado.", type=Gtk.MessageType.WARNING)
        dlg.add_buttons("OK", Gtk.ResponseType.OK)
        dlg.run(); dlg.destroy()
        return

    # 3. Extrair datas de captura (agrupa por data)
    datas = {}
    datas_sem_exif = []  # fotos que ficaram com mtime como fallback
    fontes = {'pillow': 0, 'exifread': 0, 'mtime': 0}  # estatísticas p/ diagnóstico

    # Modo debug: mostrar detalhes por ficheiro antes de agrupar
    if debug_mode:
        print("\n" + "=" * 70)
        print("DIAGNÓSTICO EXIF POR FICHEIRO")
        print("=" * 70)

    for f in principais:
        if debug_mode:
            _diagnostico_exif(f)
        dt, used_fallback, fonte = obter_data_exif(f)
        fontes[fonte] = fontes.get(fonte, 0) + 1
        datas.setdefault(dt.strftime("%Y%m%d"), []).append(f)
        if used_fallback:
            datas_sem_exif.append(os.path.basename(f))

    datas_ordenadas = sorted(datas.keys())

    if debug_mode:
        print("\n" + "=" * 70)
        print(f"RESUMO: {len(principais)} fotos, {len(datas_ordenadas)} datas distintas")
        print(f"Fontes: Pillow={fontes['pillow']}, exifread={fontes['exifread']}, mtime={fontes['mtime']}")
        for d in datas_ordenadas:
            print(f"  {d}: {len(datas[d])} foto(s) — {os.path.basename(datas[d][0])}...")
        print("=" * 70 + "\n")

    # Diagnóstico: se só há 1 data para muitas fotos, provavelmente o EXIF falhou
    if len(datas_ordenadas) == 1 and len(principais) > 3:
        d_unic = datas_ordenadas[0]
        n = len(principais)
        msg_diag = (f"⚠️ ATENÇÃO: {n} fotos foram todas agrupadas na mesma data "
                    f"({d_unic}).\nIsto pode indicar que o EXIF não foi lido corretamente.\n"
                    f"Fontes usadas: Pillow={fontes['pillow']}, "
                    f"exifread={fontes['exifread']}, mtime={fontes['mtime']}\n\n"
                    f"Verifica se as fotos têm EXIF com:\n"
                    f"  exiftool -DateTimeOriginal 01.JPG\n\n"
                    f"Continuar mesmo assim?")
        dlg_diag = Gtk.MessageDialog(text=msg_diag, type=Gtk.MessageType.WARNING)
        dlg_diag.add_buttons("Cancelar", Gtk.ResponseType.CANCEL,
                             "Continuar", Gtk.ResponseType.OK)
        res_diag = dlg_diag.run()
        dlg_diag.destroy()
        if res_diag != Gtk.ResponseType.OK:
            return

    # 4. Diálogo inicial — configurar opções
    #    Pré-carrega a última pasta usada (se existir no histórico)
    historico_eventos, historico_locais, ultima_pasta = load_history()
    ask_mode, pasta_destino = janela_principal(ultima_pasta=ultima_pasta)
    if ask_mode is None:
        return

    # 5. Para cada data distinta, pedir Evento e Local
    info = {}

    for d in datas_ordenadas:
        if ask_mode:
            res = janela_por_data(d, datas[d][0], historico_eventos, historico_locais)
            if res:
                ev_raw, loc_raw = res[0], res[1]

                # 1. Guarda no JSON exatamente como foi escrito (texto cru)
                if ev_raw not in historico_eventos:
                    historico_eventos.append(ev_raw)
                if loc_raw not in historico_locais:
                    historico_locais.append(loc_raw)

                # 2. Sanitiza APENAS para o nome da pasta
                info[d] = (sanitize(ev_raw), sanitize(loc_raw))
            else:
                info[d] = ("Evento", "Local")
        else:
            info[d] = ("Evento", "Local")

    # 6. Persistir histórico (escrita atómica) — inclui a pasta de destino
    save_history(historico_eventos, historico_locais, ultima_pasta=pasta_destino)

    # 7. Mover ficheiros e sidecars
    movidos_main, movidos_sidecar, erros, fallback_cnt = 0, 0, [], 0
    processed = set()

    # Garantir que a pasta de destino existe (pode ter sido apagada entretanto)
    os.makedirs(pasta_destino, exist_ok=True)

    for d in datas_ordenadas:
        ev_san, loc_san = info[d]
        if ev_san == "Evento" and loc_san == "Local":
            fallback_cnt += 1

        pasta = f"{d}_{ev_san}_{loc_san}"

        for f in datas[d]:
            # 7a. Skip se já processado (evita mover o mesmo sidecar 2x)
            if f in processed:
                continue

            # 7b. Pasta de destino = pasta escolhida pelo utilizador + nome da subpasta
            dir_dest = os.path.join(pasta_destino, pasta)
            os.makedirs(dir_dest, exist_ok=True)

            try:
                # 7b. Mover ficheiro principal + sidecars
                sidecars = get_sidecars(f)
                batch = [f] + sidecars
                for file_to_move in batch:
                    if file_to_move in processed:
                        continue
                    base, ext_file = os.path.splitext(os.path.basename(file_to_move))
                    dest = os.path.join(dir_dest, os.path.basename(file_to_move))

                    # Resolução de conflitos: _1, _2, ...
                    if os.path.exists(dest):
                        i = 1
                        while os.path.exists(os.path.join(dir_dest, f"{base}_{i}{ext_file}")):
                            i += 1
                        dest = os.path.join(dir_dest, f"{base}_{i}{ext_file}")

                    shutil.move(file_to_move, dest)
                    processed.add(file_to_move)
                    if file_to_move == f:
                        movidos_main += 1
                    else:
                        movidos_sidecar += 1
            except Exception as e:
                erros.append(f"{os.path.basename(f)}: {e}")

    # 8. Relatório final
    msg = f"✅ Concluído! {movidos_main} imagem(ns) e {movidos_sidecar} sidecar(s) movido(s)."
    msg += f"\n📊 Datas distintas: {len(datas_ordenadas)}"
    msg += f"\n📐 Fontes EXIF: Pillow={fontes['pillow']}, exifread={fontes['exifread']}, mtime={fontes['mtime']}"
    if fallback_cnt:
        msg += f"\n⚠️ {fallback_cnt} data(s) com nome padrão (Evento_Local)."
    if datas_sem_exif:
        n = len(datas_sem_exif)
        amostra = ", ".join(datas_sem_exif[:3])
        sufixo = "..." if n > 3 else ""
        msg += f"\n⚠️ {n} foto(s) sem EXIF (usaram data de modificação): {amostra}{sufixo}"
        if not HAS_EXIFREAD:
            msg += "\n💡 Instala 'exifread' (pip install exifread) para melhor suporte RAW."
    if erros:
        msg += f"\n❌ {len(erros)} erro(s):\n" + "\n".join(erros[:5])

    dlg = Gtk.MessageDialog(text=msg, type=Gtk.MessageType.INFO)
    dlg.add_buttons("OK", Gtk.ResponseType.OK)
    dlg.run(); dlg.destroy()


if __name__ == "__main__":
    main()