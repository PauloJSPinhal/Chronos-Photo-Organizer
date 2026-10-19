# Contribuir para o Chronos-Photo-Organizer

Obrigado pelo interesse em contribuir! 🎉

Este documento descreve como configurar o ambiente, as convenções de código e o processo para submeter alterações.

---

## 📋 Índice

- [Código de conduta](#-código-de-conduta)
- [Configuração do ambiente](#-configuração-do-ambiente)
- [Estrutura do projeto](#-estrutura-do-projeto)
- [Convenções de código](#-convenções-de-código)
- [Testes](#-testes)
- [Commits](#-commits)
- [Pull Requests](#-pull-requests)
- [Reportar bugs](#-reportar-bugs)
- [Propor funcionalidades](#-propor-funcionalidades)

---

## 🤝 Código de conduta

Participa de forma respeitosa e construtiva. Comentários pessoais, ataques ou discurso de ódio não serão tolerados. Diferenças de opinião técnica são bem-vindas desde que fundamentadas.

---

## 🔧 Configuração do ambiente

### Pré-requisitos

- Python 3.8+
- GTK 3.36+
- `pip` e `venv`

### Passo a passo

1. **Fork e clone** do repositório:

   ```bash
   git clone https://github.com/SEU-USUARIO/Chronos-Photo-Organizer.git
   cd Chronos-Photo-Organizer
   ```

2. **Criar ambiente virtual**:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Instalar dependências de desenvolvimento**:

   ```bash
   pip install -r requirements-dev.txt
   ```

   Ou manualmente:

   ```bash
   pip install Pillow pygobject exifread pytest pytest-cov flake8 black
   ```

   > ⚠️ O `pygobject` requer headers de sistema. Em Debian/Ubuntu:
   > `sudo apt install libglib2.0-dev libgtk-3-dev libgirepository1.0-dev`

4. **Instalar como Nautilus Script (opcional, para testes reais)**:

   ```bash
   ln -sf "$(pwd)/chronos.py" ~/.local/share/nautilus/scripts/Chronos.py
   chmod +x chronos.py
   ```

5. **Verificar instalação**:

   ```bash
   python3 -c "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk; print('GTK OK')"
   python3 -c "from PIL import Image; print('Pillow OK')"
   ```

---

## 📁 Estrutura do projeto

```
Chronos-Photo-Organizer/
├── chronos.py                 # Script principal (GTK3 + lógica)
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── .gitignore
├── .github/
│   └── ISSUE_TEMPLATE/
│       ├── bug-report.md
│       ├── feature-request.md
│       └── raw-not-supported.md
├── docs/                      # Screenshots e documentação extra
│   ├── dialogo-principal.png
│   ├── dialogo-por-data.png
│   └── resultado-final.png
└── tests/                     # (planeado) Testes unitários
    ├── test_sanitize.py
    ├── test_exif.py
    └── test_sidecars.py
```

---

## 📏 Convenções de código

### Estilo geral

- **PEP 8** com `black` para formatação automática
- **Linhas até 100 caracteres** (não 79 — o script tem strings longas)
- **Indentação**: 4 espaços, sem tabs
- **Encoding**: UTF-8 com header `# -*- coding: utf-8 -*-`

### Convenções específicas do projeto

| Item | Convenção | Exemplo |
|---|---|---|
| Nomes de funções | `snake_case` em PT | `obter_data_exif()` |
| Nomes de variáveis | `snake_case` em PT | `historico_eventos` |
| Constantes | `UPPER_SNAKE` em PT ou EN | `IMAGE_EXTS`, `HISTORY_FILE` |
| Comentários de secção | Box com `# ───` | ver `chronos.py` |
| Docstrings | Triple-quote duplo | `"""..."""` |
| Mensagens de UI | PT-PT natural | "Pedir Evento e Local para cada data" |

### Verificar antes de commitar

```bash
# Formatar
black chronos.py

# Lint
flake8 chronos.py --max-line-length=100

# Tipo (se adicionares typing)
mypy chronos.py --ignore-missing-imports
```

### Comentários de secção

O script usa separadores visuais para delimitar secções. Manter o padrão:

```python
# ─────────────────────────────────────────────────────────────────────────────
# 1. CONFIGURAÇÃO & HISTÓRICO
# ─────────────────────────────────────────────────────────────────────────────
```

---

## 🧪 Testes

### Estado atual

O projeto ainda **não tem suite de testes**. Esta é uma área prioritária para contribuição.

### Prioridades de teste

| Módulo | Função | Prioridade |
|---|---|---|
| Sanitização | `sanitize()` | Alta — lógica central, fácil de testar |
| EXIF | `obter_data_exif()` | Alta — lógica central |
| Sidecars | `get_sidecars()` | Média |
| Histórico | `load_history()` / `save_history()` | Média |
| UI | Diálogos GTK | Baixa — difícil de automatizar |

### Exemplo de estrutura de teste

```python
# tests/test_sanitize.py
import pytest
from chronos import sanitize

@pytest.mark.parametrize("input,expected", [
    ("Fim de semana", "Fim-de-semana"),
    ("Trás-os-Montes", "Trás-os-Montes"),
    ("São João!!", "São-João"),
    ("A -- B", "A-B"),
    ("-Natal-", "Natal"),
    ("", "Indefinido"),
    (None, None),
])
def test_sanitize(input, expected):
    assert sanitize(input) == expected
```

### Executar testes

```bash
pytest tests/ -v --cov=chronos
```

---

## 📝 Commits

### Formato

Seguir [Conventional Commits](https://www.conventionalcommits.org/):

```
<tipo>(<scope>): <descrição>

<corpo opcional>

<footer opcional>
```

### Tipos

| Tipo | Quando usar |
|---|---|
| `feat` | Nova funcionalidade |
| `fix` | Correção de bug |
| `docs` | Apenas documentação |
| `style` | Formatação, sem mudança de código |
| `refactor` | Refactor sem mudança de comportamento |
| `perf` | Melhoria de performance |
| `test` | Adicionar/corrigir testes |
| `chore` | Tarefas de manutenção |

### Exemplos

```bash
git commit -m "feat(exif): adicionar fallback para exifread em RAWs"
git commit -m "fix(sanitize): preservar underscores em nomes de eventos"
git commit -m "docs(readme): adicionar secção de formatos RAW suportados"
git commit -m "refactor(history): usar escrita atómica via os.replace"
```

---

## 🔄 Pull Requests

### Antes de submeter

- [ ] Código formatado com `black`
- [ ] `flake8` sem warnings
- [ ] Testes adicionados para nova funcionalidade
- [ ] Todos os testes a passar
- [ ] `CHANGELOG.md` atualizado em [Unreleased]
- [ ] Commits seguem Conventional Commits

### Processo

1. **Criar branch** a partir de `main`:

   ```bash
   git checkout -b feat/minha-funcionalidade
   ```

2. **Fazer commits pequenos e atómicos** — cada commit deve deixar o código funcional.

3. **Push e abrir PR**:

   ```bash
   git push origin feat/minha-funcionalidade
   ```

4. **No PR, descrever**:
   - O que muda e porquê
   - Como testar manualmente
   - Screenshots (se alterar UI)
   - Issues fechadas (`Closes #123`)

### Critérios de aceitação

- ✅ Mantém o espírito do projeto: **simples, sem dependências pesadas**
- ✅ Não quebra compatibilidade com versões anteriores (a menos que seja major)
- ✅ Código em PT-PT coerente com o resto do script
- ✅ Não introduz dependências desnecessárias (cada nova dep precisa de justificação)

---

## 🐛 Reportar bugs

Usar o template [bug-report.md](./.github/ISSUE_TEMPLATE/bug-report.md).

Informações essenciais:

- Versão do Chronos (`grep VERSION chronos.py` ou ver `CHANGELOG.md`)
- Distribuição Linux e versão do GNOME
- Versão do Python e do PyGObject
- Formato dos ficheiros envolvidos (JPEG, CR3, NEF, ...)
- Passos para reproduzir
- Output de erro (se houver)

Executar em modo debug para recolher informação útil:

```bash
GTK_DEBUG=all PYTHONPATH=. python3 chronos.py foto.jpg 2>&1 | tee debug.log
```

---

## 💡 Propor funcionalidades

Usar o template [feature-request.md](./.github/ISSUE_TEMPLATE/feature-request.md).

Antes de abrir uma issue de funcionalidade, verificar:

- [ ] A funcionalidade está alinhada com o objetivo do projeto (organização de fotos por data)
- [ ] Não existe já uma issue aberta para o mesmo tema
- [ ] A funcionalidade não pode ser resolvida com ferramentas externas (ex.: `exiftool`)

### Áreas onde contribuições são especialmente bem-vindas

- 🧪 **Testes automatizados** — qualquer cobertura é valiosa
- 🌍 **Internacionalização** — extrair strings para `.po`/`.mo`
- ⚡ **Performance** — thumbnails assíncronos, leitura EXIF paralela
- 📦 **Empacotamento** — pacotes `.deb`, `.rpm`, AUR
- 🪟 **Porting Windows** — usando PyGObject + MSYS2 (experimental)

---

## ❓ Dúvidas

- Abrir uma [issue](https://github.com/Chronos-Photo-Organizer/issues) com a label `question`
- Ou contactar via discussões do GitHub (se ativadas)

Obrigado por contribuir! 🚀
