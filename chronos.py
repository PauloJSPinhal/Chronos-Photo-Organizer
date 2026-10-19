#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Organizar Fotos por Data (Nautilus Script) - v5.3
Formato: AAAAMMDD_Evento-Local
Histórico ComboBox (texto cru) + Sanitização Inteligente (hífens preservados)
Interface GTK3 nativa, tema dark herdado, PyGObject.
"""

import sys, os, shutil, datetime, urllib.parse, re, io, json
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf
from PIL import Image

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

def load_history():
    try:
        if os.path.isfile(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("eventos", []), data.get("locais", [])
    except Exception:
        pass
    return [], []

def save_history(eventos, locais):
    os.makedirs(HISTORY_DIR, exist_ok=True)
    data = {
        "eventos": sorted(list(set(eventos))),
        "locais": sorted(list(set(locais)))
    }
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ─────────────────────────────────────────────────────────────────────────────
# 2. EXTRAÇÃO EXIF & SIDECARS
# ─────────────────────────────────────────────────────────────────────────────
def obter_data_exif(caminho):
    try:
        with Image.open(caminho) as img:
            exif = getattr(img, 'getexif', lambda: getattr(img, '_getexif', lambda: None)())()
            if exif:
                for tag_id in [36867, 36868, 306]:
                    val = exif.get(tag_id)
                    if not val: continue
                    dt_str = val.decode('utf-8', errors='ignore').strip('\x00') if isinstance(val, bytes) else str(val).strip()
                    try:
                        return datetime.datetime.strptime(dt_str[:19], "%Y:%m:%d %H:%M:%S"), False
                    except ValueError:
                        try:
                            return datetime.datetime.strptime(dt_str[:10], "%Y:%m:%d"), False
                        except ValueError:
                            continue
    except Exception:
        pass
    return datetime.datetime.fromtimestamp(os.path.getmtime(caminho)), True

def get_sidecars(main_file):
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
    """
    - Substitui espaços por hífens (Fim de semana -> Fim-de-semana)
    - Preserva hífens existentes (Trás-os-Montes -> Trás-os-Montes)
    - Remove caracteres inválidos mas mantém acentos
    - Limpa hífens duplos resultantes de digitação errada
    """
    if not text: return text
    t = text.strip()
    
    # 1. Substitui espaços por hífens
    t = t.replace(' ', '-')
    
    # 2. Remove caracteres que não são letras, números, acentos ou hífens
    # \w em Python 3 já inclui caracteres Unicode (acentos)
    t = re.sub(r'[^\w-]', '', t, flags=re.UNICODE)
    
    # 3. Se houver hífens repetidos (ex: "A--B" ou "---"), colapsa para um
    t = re.sub(r'-+', '-', t)
    
    # 4. Remove hífens no início ou fim se existirem
    return t.strip('-') or "Indefinido"

def image_to_pixbuf(filepath, max_size=280):
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in IMAGE_EXTS: return None
    try:
        with Image.open(filepath) as img:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            if img.mode != 'RGB': img = img.convert('RGB')
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
def janela_principal():
    win = Gtk.Dialog(title="Organizar Fotos por Data", default_width=380)
    win.set_resizable(False)
    win.set_position(Gtk.WindowPosition.CENTER)
    win.set_border_width(20)
    box = win.get_content_area()
    box.set_spacing(15)

    lbl = Gtk.Label(label="Agrupar fotos por data de captura.\nConfigure as opções:")
    lbl.set_xalign(0); lbl.set_line_wrap(True)
    box.pack_start(lbl, False, False, 0)

    check_ask = Gtk.CheckButton(label="Pedir Evento e Local para cada data")
    check_ask.set_active(True)
    box.pack_start(check_ask, False, False, 8)

    check_up = Gtk.CheckButton(label="Criar pasta(s) um nível acima")
    check_up.set_active(False)
    box.pack_start(check_up, False, False, 8)

    win.add_button("Cancelar", Gtk.ResponseType.CANCEL)
    btn = win.add_button("Iniciar", Gtk.ResponseType.OK)
    btn.get_style_context().add_class(Gtk.STYLE_CLASS_SUGGESTED_ACTION)
    win.show_all()
    res = win.run()
    win.destroy()
    
    if res == Gtk.ResponseType.OK:
        return check_ask.get_active(), check_up.get_active()
    return None, None

def janela_por_data(data_str, caminho_foto, hist_ev, hist_loc):
    dlg = Gtk.Dialog(title=f"📅 {data_str}", default_width=420)
    dlg.set_position(Gtk.WindowPosition.CENTER)
    dlg.set_border_width(20)
    dlg.set_resizable(False)
    box = dlg.get_content_area()
    box.set_spacing(15)

    pixbuf = image_to_pixbuf(caminho_foto)
    img = Gtk.Image.new_from_pixbuf(pixbuf) if pixbuf else Gtk.Image.new_from_icon_name("image-x-generic-symbolic", Gtk.IconSize.DIALOG)
    box.pack_start(img, True, True, 10)

    grid = Gtk.Grid()
    grid.set_row_spacing(10)
    grid.set_column_spacing(10)
    grid.set_halign(Gtk.Align.CENTER)

    combo_ev = Gtk.ComboBoxText.new_with_entry()
    for ev in hist_ev: combo_ev.append_text(ev)
    combo_ev.set_entry_text_column(0)

    combo_loc = Gtk.ComboBoxText.new_with_entry()
    for loc in hist_loc: combo_loc.append_text(loc)
    combo_loc.set_entry_text_column(0)

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
def main():
    uris = sys.argv[1:]
    ficheiros = [urllib.parse.unquote(u[7:]) if u.startswith("file://") else os.path.abspath(u) for u in uris if os.path.isfile(u)]
    if not ficheiros:
        dlg = Gtk.MessageDialog(text="Nenhuma foto válida selecionada.", type=Gtk.MessageType.ERROR)
        dlg.add_buttons("OK", Gtk.ResponseType.OK)
        dlg.run(); dlg.destroy()
        return

    principais = [f for f in ficheiros if os.path.splitext(f)[1].lower() in IMAGE_EXTS]
    if not principais:
        dlg = Gtk.MessageDialog(text="Nenhum ficheiro de imagem/RAW selecionado.", type=Gtk.MessageType.WARNING)
        dlg.add_buttons("OK", Gtk.ResponseType.OK)
        dlg.run(); dlg.destroy()
        return

    datas = {}
    for f in principais:
        dt, _ = obter_data_exif(f)
        datas.setdefault(dt.strftime("%Y%m%d"), []).append(f)
    datas_ordenadas = sorted(datas.keys())

    ask_mode, one_level_up = janela_principal()
    if ask_mode is None: return

    historico_eventos, historico_locais = load_history()
    info = {}

    for d in datas_ordenadas:
        if ask_mode:
            res = janela_por_data(d, datas[d][0], historico_eventos, historico_locais)
            if res:
                ev_raw, loc_raw = res[0], res[1]
                
                # 1. Guarda no JSON exatamente como foi escrito
                if ev_raw not in historico_eventos: historico_eventos.append(ev_raw)
                if loc_raw not in historico_locais: historico_locais.append(loc_raw)
                
                # 2. Sanitiza APENAS para o nome da pasta
                info[d] = (sanitize(ev_raw), sanitize(loc_raw))
            else:
                info[d] = ("Evento", "Local")
        else:
            info[d] = ("Evento", "Local")

    save_history(historico_eventos, historico_locais)

    movidos_main, movidos_sidecar, erros, fallback_cnt = 0, 0, [], 0
    processed = set()

    for d in datas_ordenadas:
        ev_san, loc_san = info[d]
        if ev_san == "Evento" and loc_san == "Local":
            fallback_cnt += 1

        pasta = f"{d}_{ev_san}_{loc_san}"

        for f in datas[d]:
            current_dir = os.path.dirname(f) or "."
            dir_base = os.path.dirname(current_dir) if one_level_up else current_dir
            
            dir_dest = os.path.join(dir_base, pasta)
            os.makedirs(dir_dest, exist_ok=True)

            if f in processed: continue

            try:
                sidecars = get_sidecars(f)
                batch = [f] + sidecars
                for file_to_move in batch:
                    if file_to_move in processed: continue
                    base, ext_file = os.path.splitext(os.path.basename(file_to_move))
                    dest = os.path.join(dir_dest, os.path.basename(file_to_move))
                    if os.path.exists(dest):
                        i = 1
                        while os.path.exists(os.path.join(dir_dest, f"{base}_{i}{ext_file}")):
                            i += 1
                        dest = os.path.join(dir_dest, f"{base}_{i}{ext_file}")
                    shutil.move(file_to_move, dest)
                    processed.add(file_to_move)
                    if file_to_move == f: movidos_main += 1
                    else: movidos_sidecar += 1
            except Exception as e:
                erros.append(f"{os.path.basename(f)}: {e}")

    msg = f"✅ Concluído! {movidos_main} imagem(ns) e {movidos_sidecar} sidecar(s) movido(s)."
    if fallback_cnt: msg += f"\n⚠️ {fallback_cnt} data(s) com nome padrão (Evento-Local)."
    if erros: msg += f"\n❌ {len(erros)} erro(s):\n" + "\n".join(erros[:5])

    dlg = Gtk.MessageDialog(text=msg, type=Gtk.MessageType.INFO)
    dlg.add_buttons("OK", Gtk.ResponseType.OK)
    dlg.run(); dlg.destroy()

if __name__ == "__main__":
    main()