# Changelog

Todos os lançamentos notáveis do **Chronos-Photo-Organizer** são documentados neste ficheiro.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e o projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

---

## [Unreleased]

### Planeado
- Diálogo de gestão de histórico (apagar entradas obsoletas)
- Thumbnail assíncrono para não bloquear a UI
- Suporte a vídeos (extração de data via `ffmpeg`)
- Modo batch: processar múltiplas pastas em fila

---

## [5.5] — 2024

### Adicionado
- **Seletor de pasta de destino** via `Gtk.FileChooserDialog` — substitui o
  antigo checkbox "Criar pasta(s) um nível acima". Agora o utilizador pode
  escolher explicitamente onde as pastas `AAAAMMDD_Evento_Local` serão criadas,
  com navegação real pelo sistema de ficheiros.
- **Pasta inicial do filechooser**: `/home/$USER/Imagens` (criada automaticamente
  se não existir). Garante que o diálogo abre num local útil, não em `/`.
- **Persistência da última pasta escolhida** — guardada no `historico.json`
  sob a chave `ultima_pasta`. Na próxima execução, o diálogo inicial abre
  com essa pasta já pré-selecionada.
- **Label visível na janela inicial** mostra o caminho completo da pasta
  escolhida (com `ellipsize=MIDDLE` para caminhos longos).

### Removido
- **Checkbox "Criar pasta(s) um nível acima"** — substituído pelo seletor
  de pasta, que é mais flexível e explícito. O comportamento equivalente
  pode ser obtido escolhendo a pasta pai no filechooser.

### Alterado
- `janela_principal()` passa a aceitar o parâmetro `ultima_pasta=None`
  para pré-preencher o campo de destino.
- `load_history()` retorna 3 valores: `(eventos, locais, ultima_pasta)`.
- `save_history()` aceita o parâmetro `ultima_pasta=None` para persistir
  a escolha do utilizador.
- Lógica de movimentação simplificada: `dir_dest = pasta_destino + pasta`
  em vez do cálculo `current_dir` / `dir_base` anterior.
- Garantia de criação da pasta de destino (`os.makedirs(pasta_destino,
  exist_ok=True)`) antes do loop de processamento — protege contra pastas
  apagadas entretanto.

---

## [5.4] — 2024

### Adicionado
- **Fallback `exifread` para extração fiável de datas em ficheiros RAW** — quando o
  Pillow não consegue abrir um RAW (CR2, NEF, ARW, etc.), o `exifread` lê os bytes
  EXIF brutos sem decodificar pixels, evitando o fallback para `mtime`.
  O `exifread` é uma dependência opcional — se não estiver instalado, o script
  continua a funcionar, mas volta a usar `mtime` para RAWs.
- **Diálogo de final com aviso de fotos sem EXIF** — lista as primeiras 3 fotos
  que ficaram com data de modificação (em vez de captura), e sugere instalar
  `exifread` se for o caso.
- **Sugestão de instalação do `exifread`** no relatório final quando aplicável.

### Corrigido
- **Filtro de URIs `file://` do Nautilus** — anteriormente, `os.path.isfile(u)`
  era avaliado antes de remover o prefixo `file://`, pelo que nenhum ficheiro
  vindo do Nautilus passava o filtro. Agora a normalização acontece primeiro,
  via função dedicada `_normalizar_uri()`.
- **Removida tag EXIF 306 (`DateTime`)** da lista de tags tentadas — esta tag
  representa a data de modificação do ficheiro, não a data de captura. Estava
  a corromper datas em fotos pós-processadas (exportadas, editadas).
  Lista de tags reduzida para `(36867, 36868)` apenas.
- **Sanitização agora substitui underscores por hífens** — evita o bug
  `20240101_Festa_Casa_Local` (com 2 underscores como separador), garantindo
  separador único e consistente.
- **`sanitize('')` agora retorna `'Indefinido'`** em vez de string vazia —
  anteriormente, o early return `if not text: return text` impedia o fallback.
- **Check `if f in processed` movido para antes de `os.makedirs()`** — evita
  chamada desnecessária ao sistema para ficheiros já processados.

### Alterado
- **Escrita atómica do `historico.json`** via `os.replace()` — grava para
  `.tmp` e faz rename atómico, evitando corrupção se o processo for
  interrompido a meio do `json.dump`.
- **Refactor de `obter_data_exif()`** em 3 funções especializadas:
  `_exif_from_pillow()`, `_exif_from_exifread()`, `_parse_exif_date()`.
  Mais fácil de testar e manter.
- **`getexif()` chamado directamente** (Pillow 10+) em vez do `getattr` com
  fallback para `_getexif()` (removido em Pillow ≥ 10).
- **Diálogos GTK3 com `set_modal(True)`** — comportamento mais previsível
  em diferentes window managers.
- **Título do diálogo principal** atualizado para "Chronos — Organizar
  Fotos por Data" (era apenas "Organizar Fotos por Data").

---

## [5.3] — 2024

### Adicionado
- Sanitização inteligente que preserva acentos e hífens existentes
  (ex.: "Trás-os-Montes" mantém-se correto)
- Histórico ComboBox com texto cru — guarda o que o utilizador escreveu
  exatamente, sem normalização, para garantir legibilidade futura
- Opção "Criar pasta(s) um nível acima" no diálogo principal
- Suporte a sidecars nos padrões `ficheiro.xmp` e `ficheiro.ext.xmp`
  (cobertura completa para Adobe, RawTherapee e DxO)

### Alterado
- `sanitize()` agora usa regex `[^\w-]` com flag `re.UNICODE` para preservar
  todos os caracteres alfanuméricos Unicode, incluindo acentos
- Histórico JSON passa a usar `ensure_ascii=False` para guardar acentos
  legivelmente em vez de sequências `\uXXXX`

### Corrigido
- Hífens duplos resultantes de digitação errada ("A--B") são agora colapsados
  para um único hífen
- Hífens no início ou fim do nome da pasta são removidos
- Fallback para "Indefinido" quando input sanitizado fica vazio

---

## [5.2] — 2024

### Adicionado
- Suporte a 29 extensões RAW (CR2, CR3, NEF, ARW, DNG, ORF, RW2, PEF, SRW,
  RAF, IIQ, KDC, MOS, MEF, NRW, R3D, GPR, ERF, etc.)
- Detecção automática de ficheiros sidecar (XMP, PP3, DOP)
- Resolução de conflitos de nomes com sufixo `_1`, `_2`, ...
- Controlo `processed` (set) para evitar mover o mesmo sidecar duas vezes
  quando existe par RAW + JPEG com XMP partilhado

### Alterado
- Refatorização do módulo de extração EXIF para usar `getexif()` (Pillow 10+)
  em vez de `_getexif()` (removido em versões modernas)
- Lista de tags EXIF expandida para incluir `DateTimeOriginal` (36867),
  `DateTimeDigitized` (36868) e `DateTime` (306) como fallback

---

## [5.1] — 2024

### Adicionado
- Pré-visualização de thumbnail da primeira foto de cada data no diálogo
  "Por data" (max 280px, redimensionamento LANCZOS)
- Tema dark herdado do GNOME via `GTK_THEME=Adwaita:dark`
- Validação de campos no diálogo "Por data" — botão OK só fica ativo quando
  Evento e Local estão ambos preenchidos

### Alterado
- Diálogo principal redesenhado com checkboxes em vez de botões radio
- Mensagem de final expandida com contadores de sidecars movidos e erros

---

## [5.0] — 2024

### Adicionado
- Primeira versão pública do Chronos
- Arquitetura modular: configuração, EXIF, sanitização, diálogos GTK,
  lógica principal — em secções claramente separadas
- Histórico JSON persistente em `~/.config/organizar_fotos/historico.json`
- Integração como Nautilus Script em `~/.local/share/nautilus/scripts/`
- Formato de nome de pasta `AAAAMMDD_Evento_Local`
- Suporte inicial a JPEG, PNG, TIFF, WebP, BMP, GIF
- Suporte a URIs `file://` (formato recebido do Nautilus)

---

## Convenções de versão

- **Major** (X.0): quebras de compatibilidade ou refactor profundo
- **Minor** (X.Y): novas funcionalidades, compatibilidade mantida
- **Patch** (X.Y.Z): correções de bugs apenas

---

## Links

- [Comparar versões](https://github.com/Chronos-Photo-Organizer/compare)
- [Releases](https://github.com/Chronos-Photo-Organizer/releases)