# Chronos-Photo-Organizer

> Script GTK3 (Nautilus) para organizar fotografias por data de captura EXIF, com suporte a ficheiros RAW e sidecars XMP/PP3/DOP.

[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![GTK3](https://img.shields.io/badge/GTK-3.0-green.svg)](https://www.gtk.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20BSD-lightgrey.svg)](https://github.com/Chronos-Photo-Organizer)
[![Version](https://img.shields.io/badge/version-5.5-orange.svg)](./CHANGELOG.md)

---

## 📋 Índice

- [Descrição](#-descrição)
- [Funcionalidades](#-funcionalidades)
- [Screenshots](#-screenshots)
- [Requisitos](#-requisitos)
- [Instalação](#-instalação)
- [Utilização](#-utilização)
- [Convenção de nomes](#-convenção-de-nomes)
- [Formatos suportados](#-formatos-suportados)
- [Histórico de eventos e locais](#-histórico-de-eventos-e-locais)
- [Sanitização inteligente](#-sanitização-inteligente)
- [Limitações conhecidas](#-limitações-conhecidas)
- [Roadmap](#-roadmap)
- [Contribuir](#-contribuir)
- [Changelog](#-changelog)
- [Licença](#-licença)

---

## 📖 Descrição

O **Chronos** é um script Python + GTK3 desenhado para integrar no menu de scripts do Nautilus (GNOME Files). Permite selecionar um conjunto de fotografias (JPEG, TIFF, PNG ou RAW de qualquer câmara moderna) e organizá-las automaticamente em pastas com base na **data real de captura** extraída dos metadados EXIF — e não na data de modificação do ficheiro.

Para cada data distinta, o script abre um diálogo GTK que mostra um thumbnail da primeira foto dessa data e pede ao utilizador um **Evento** e um **Local**. Esses valores, combinados com a data, formam o nome da pasta destino no formato `AAAAMMDD_Evento_Local`. O histórico de eventos e locais é guardado em JSON para auto-completar em utilizações futuras.

O script move também os **ficheiros sidecar** associados a cada fotografia (`.xmp`, `.pp3`, `.dop`), preservando o trabalho de edição feito em ferramentas como Darktable, RawTherapee ou DxO PhotoLab.

---

## ✨ Funcionalidades

- 📅 **Agrupamento por data de captura EXIF** (Tag 36867 `DateTimeOriginal`), não por data de modificação do ficheiro.
- 🖼️ **Pré-visualização** da primeira foto de cada data no diálogo de configuração.
- 🗂️ **Suporte a sidecars** XMP, PP3 e DOP — move-os automaticamente com a foto principal.
- ⌨️ **Histórico persistente** de eventos e locais em `~/.config/organizar_fotos/historico.json`, com auto-completar via ComboBox.
- 🧹 **Sanitização inteligente** de nomes: preserva acentos e hífens existentes (ex.: "Trás-os-Montes"), substitui espaços por hífens, normaliza separadores duplicados.
- 🌙 **Tema dark herdado** do GNOME — sem ofuscar os olhos em sessões de edição noturnas.
- 📁 **Seletor de pasta de destino** via `Gtk.FileChooserDialog` — abre em `~/Imagens`, persiste a última escolha.
- 🔁 **Resolução de conflitos** automática com sufixo `_1`, `_2`, ... quando já existe ficheiro com o mesmo nome.
- 🎞️ **29 extensões RAW suportadas**: CR2, CR3, NEF, ARW, DNG, ORF, RW2, PEF, SRW, RAF, etc.

---

## 📸 Screenshots

> Substituir os placeholders abaixo pelas capturas de ecrã reais depois de carregar para a pasta `docs/`.

<!-- ![Diálogo principal](docs/dialogo-principal.png) -->
<!-- ![Diálogo por data com thumbnail](docs/dialogo-por-data.png) -->
<!-- ![Resultado final — pastas criadas](docs/resultado-final.png) -->

**Para gerar as capturas**, executar:

```bash
gnome-screenshot -w -d 2 -f docs/dialogo-principal.png
```

---

## 🔧 Requisitos

| Dependência | Versão mínima | Notas |
|---|---|---|
| Python | 3.8+ | Testado até 3.12 |
| PyGObject (`gir1.2-gtk-3.0`) | 3.36+ | Binding GTK3 para Python |
| Pillow | 10.0+ | Leitura EXIF e geração de thumbnails |
| GTK 3 | 3.36+ | Incluído em qualquer GNOME recente |
| Nautilus | 40+ | Para integração como script (opcional) |

### Instalar dependências (Debian/Ubuntu)

```bash
sudo apt install python3-gi python3-pil gir1.2-gtk-3.0 nautilus
```

### Instalar dependências (Arch/Manjaro)

```bash
sudo pacman -S python-gobject python-pillow gtk3 nautilus
```

### Instalar dependências (Fedora)

```bash
sudo dnf install python3-gobject python3-pillow gtk3 nautilus
```

---

## 📥 Instalação

### Opção A — Instalação como Nautilus Script (recomendado)

1. Criar a pasta de scripts do Nautilus (se não existir):

   ```bash
   mkdir -p ~/.local/share/nautilus/scripts
   ```

2. Copiar o script para essa pasta com nome curto:

   ```bash
   cp chronos.py ~/.local/share/nautilus/scripts/Chronos.py
   chmod +x ~/.local/share/nautilus/scripts/Chronos.py
   ```

3. Reiniciar o Nautilus:

   ```bash
   nautilus -q
   ```

4. Agora, ao selecionar fotos no Nautilus → botão direito → **Scripts → Chronos.py**.

### Opção B — Uso standalone (linha de comandos)

```bash
chmod +x chronos.py
./chronos.py foto1.jpg foto2.cr3 foto3.nef
```

Os argumentos podem ser paths absolutos ou URIs `file://` (formato recebido do Nautilus).

---

## 🚀 Utilização

1. Selecionar um conjunto de fotografias no Nautilus (JPEG + RAW misturados, sem problema).
2. Botão direito → **Scripts → Chronos.py**.
3. No diálogo inicial, escolher:
   - ✅ **Pedir Evento e Local para cada data** (recomendado) — abre um diálogo por data distinta.
   - 📁 **Pasta de destino** — clica em **Procurar...** para abrir um navegador de ficheiros que abre em `~/Imagens`. A pasta escolhida fica visível no diálogo e é guardada para a próxima execução.
4. Para cada data distinta, o diálogo mostra um thumbnail da primeira foto dessa data. Preencher **Evento** e **Local** (com auto-completar do histórico). Ambos os campos têm de estar preenchidos para o botão **OK** ficar ativo.
5. Confirmar com **OK** ou cancelar (a data fica com nome padrão `Evento_Local`).
6. No fim, aparece um resumo com:
   - Nº de imagens movidas
   - Nº de sidecars movidos
   - Datas que ficaram com nome padrão (fallback)
   - Erros ocorridos (se algum)

---

## 📂 Convenção de nomes

As pastas criadas seguem o formato:

```
AAAAMMDD_Evento_Local
```

### Exemplos

| Data de captura | Evento | Local | Pasta resultante |
|---|---|---|---|
| 2024-01-15 | Casamento | Porto | `20240115_Casamento_Porto` |
| 2024-03-08 | Fim de semana | Trás-os-Montes | `20240308_Fim-de-semana_Trás-os-Montes` |
| 2024-07-22 | Viagem | Aveiro | `20240722_Viagem_Aveiro` |
| 2024-12-25 | Natal | Lisboa | `20241225_Natal_Lisboa` |

### Regras de sanitização

1. **Espaços → hífens** (`Fim de semana` → `Fim-de-semana`)
2. **Hífens existentes são preservados** (`Trás-os-Montes` → mantém-se)
3. **Acentos são mantidos** (UTF-8 native)
4. **Caracteres inválidos removidos** (símbolos, pontuação)
5. **Hífens duplos colapsados** (`A--B` → `A-B`)
6. **Hífens nas pontas removidos** (`-Natal-` → `Natal`)

> ⚠️ O histórico JSON guarda o texto **cru** tal como foi escrito. A sanitização só é aplicada ao nome da pasta, mantendo o histórico legível.

---

## 🎞️ Formatos suportados

### Imagens raster

`.jpg` `.jpeg` `.png` `.tiff` `.tif` `.webp` `.bmp` `.gif`

### RAW (29 formatos)

| Fabricante | Extensões |
|---|---|
| Canon | `.cr2` `.cr3` |
| Nikon | `.nef` `.nrw` |
| Sony | `.arw` `.sr2` `.srf` |
| Adobe (universal) | `.dng` |
| Olympus | `.orf` |
| Panasonic/Leica | `.rw2` `.raw` |
| Pentax | `.pef` |
| Samsung | `.srw` |
| Fujifilm | `.raf` |
| Phase One | `.iiq` |
| Kodak | `.kdc` `.dcr` |
| Leaf | `.mos` |
| Mamiya | `.mef` |
| Red | `.r3d` |
| Sigma | `.x3f` |
| GoPro | `.gpr` |
| Epson | `.erf` |

### Sidecars

| Extensão | Software que gera |
|---|---|
| `.xmp` | Adobe Camera Raw, Darktable, Lightroom |
| `.pp3` | RawTherapee |
| `.dop` | DxO PhotoLab |

O script detecta automaticamente sidecars nos padrões `ficheiro.xmp` e `ficheiro.jpg.xmp`.

---

## 💾 Histórico de eventos e locais

O Chronos mantém um histórico JSON em:

```
~/.config/organizar_fotos/historico.json
```

### Estrutura

```json
{
  "eventos": [
    "Casamento",
    "Fim de semana",
    "Viagem"
  ],
  "locais": [
    "Aveiro",
    "Lisboa",
    "Porto",
    "Trás-os-Montes"
  ],
  "ultima_pasta": "/home/utilizador/Imagens/2024"
}
```

- Os valores de `eventos` e `locais` são guardados **exatamente como escritos** (texto cru, com acentos e espaços).
- `ultima_pasta` guarda a última pasta de destino escolhida no diálogo inicial, para re-aparecer pré-selecionada na próxima execução.
- A ordenação é alfabética, automática ao gravar.
- Os duplicados são eliminados via `set()`.
- Em diálogos futuros, estes valores aparecem como sugestões no ComboBox.

### Backup do histórico

Para mover entre máquinas:

```bash
cp ~/.config/organizar_fotos/historico.json ~/dotfiles/chronos/
```

---

## 🧹 Sanitização inteligente

A função `sanitize()` (em `chronos.py`, linha ~174) é o coração da coerência dos nomes de pasta. Aplica as seguintes transformações:

| Input | Output | Notas |
|---|---|---|
| `Fim de semana` | `Fim-de-semana` | Espaços → hífens |
| `Trás-os-Montes` | `Trás-os-Montes` | Hífens existentes preservados |
| `São João!!` | `São-João` | Pontuação removida, acentos mantidos |
| `A -- B` | `A-B` | Hífens duplos colapsados |
| `-Natal-` | `Natal` | Hífens nas pontas removidos |
| `Festa_Casa` | `Festa-Casa` | Underscores → hífens (separador consistente) |
| `(vazio)` | `Indefinido` | Fallback quando input vazio |

### Expressão regular principal

```python
re.sub(r'[^\w-]', '', t, flags=re.UNICODE)  # \w em Python 3 já inclui acentos
```

---

## ⚠️ Limitações conhecidas

1. **Datas em RAW podem usar mtime como fallback** — se o Pillow não conseguir extrair EXIF e o `exifread` não estiver instalado, a data de modificação é usada. Recomenda-se instalar `exifread` (`pip install exifread`) para suporte completo a RAWs. O script avisa no relatório final quando isto acontece.

2. **Thumbnail síncrono** — a geração de thumbnails em RAWs grandes pode bloquear a UI por 1-3 segundos por foto. Solução planeada: carregar thumbnails em thread.

3. **Sem undo** — uma vez movidos os ficheiros, não há opção de reverter dentro do script. Recomenda-se fazer um teste com 2-3 fotos antes de processar grandes lotes.

4. **Histórico não tem UI de gestão** — não é possível apagar entradas obsoletas do histórico a partir da interface. Funcionalidade planeada para v5.4.

5. **Apenas Linux/BSD** — por depender de GTK3 via PyGObject, não funciona em Windows ou macOS sem porting significativo.

---

## 🗺️ Roadmap

- [x] **v5.4** — Integração com `exifread` para extração fiável de datas em RAWs ✅
- [x] **v5.4** — Corrigir filtro `file://` em URIs do Nautilus ✅
- [x] **v5.4** — Escrita atómica do `historico.json` (via `os.replace`) ✅
- [x] **v5.5** — Seletor de pasta de destino via `Gtk.FileChooserDialog` ✅
- [x] **v5.5** — Persistência da última pasta escolhida ✅
- [ ] **v5.6** — Diálogo de gestão de histórico (apagar entradas obsoletas)
- [ ] **v5.6** — Thumbnail assíncrono (não bloquear UI)
- [ ] **v5.7** — Modo batch: processar múltiplas pastas em fila
- [ ] **v5.7** — Suporte a vídeos (extração de data via `ffmpeg`)
- [ ] **v6.0** — Versão standalone (fora do Nautilus) com drag-and-drop

---

## 🤝 Contribuir

Consulte [`CONTRIBUTING.md`](./CONTRIBUTING.md) para:

- Configuração do ambiente de desenvolvimento
- Estilo de código (PEP 8 + convenções do projeto)
- Como reportar bugs e propor funcionalidades
- Formato dos commits e PRs

Contribuições são bem-vindas, especialmente:

- Testes com formatos RAW menos comuns
- Traduções da UI para outros idiomas
- Otimização da geração de thumbnails

---

## 📝 Changelog

Histórico completo de versões em [`CHANGELOG.md`](./CHANGELOG.md).

Versão atual: **v5.5** (2024)

---

## 📄 Licença

Distribuído sob licença **MIT**. Consulte [`LICENSE`](./LICENSE) para o texto completo.

```
MIT License

Copyright (c) 2024 Chronos-Photo-Organizer

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
...
```

---

## 🙋 Autor

Desenvolvido para uso pessoal, partilhado na esperança de ser útil.

Para questões, abrir uma [issue](https://github.com/Chronos-Photo-Organizer/issues/new) no GitHub.

---

<p align="center">
  Feito com ☕ e GTK3 em Portugal
</p>