---
name: 🎞️ RAW não suportado / data errada
about: Reporta um formato RAW onde o Chronos não extrai a data corretamente
title: "[RAW] "
labels: ["bug", "RAW", "triagem"]
assignees: []
---

## 📷 Formato RAW reportado

- **Extensão**: [ex.: .iiq, .kdc, .x3f, .mef]
- **Câmara**: [ex.: Phase One IQ4, Kodak DCS Pro, Sigma dp2]
- **Ano approx. da câmara**: [ex.: 2019]

## 🐛 Sintoma

<!-- Marca com [x] o sintoma observado -->

- [ ] Aparece a mensagem "Nenhuma foto válida selecionada" (filtro inicial)
- [ ] As fotos são agrupadas, mas todas caem na data de **modificação do ficheiro** (mtime)
      em vez da data real de captura
- [ ] As fotos são ignoradas e não aparecem no diálogo
- [ ] Aparece um erro na consola / no diálogo final
- [ ] O thumbnail não aparece no diálogo "Por data"
- [ ] Outro (descrever abaixo):

## 🔍 Diagnóstico

### Confirmar que a foto TEM data de captura

Executar (substituir `foto.ext` pelo ficheiro real):

```bash
# Method 1: exiftool (se instalado)
exiftool -DateTimeOriginal -DateTimeDigitized foto.ext

# Method 2: exifread (Python)
python3 -c "
import exifread
with open('foto.ext', 'rb') as f:
    tags = exifread.process_file(f, details=False)
for k in ['EXIF DateTimeOriginal', 'EXIF DateTimeDigitized', 'Image DateTime']:
    if k in tags:
        print(f'{k}: {tags[k]}')
"
```

- **Output do exiftool**:
  ```
  (colar aqui)
  ```

- **Output do exifread**:
  ```
  (colar aqui)
  ```

### Verificar se o Pillow consegue abrir o ficheiro

```bash
python3 -c "
from PIL import Image
try:
    with Image.open('foto.ext') as img:
        print(f'Formato: {img.format}')
        print(f'Size: {img.size}')
        exif = img.getexif()
        print(f'EXIF tags: {list(exif.keys())[:10]}')
except Exception as e:
    print(f'Erro: {e}')
"
```

- **Output**:
  ```
  (colar aqui)
  ```

## 📎 Amostra partilhada

<!-- Se puderes partilhar UMA foto de exemplo (pode ser uma foto qualquer
     da mesma câmara, não precisa de ser pessoal), acelera muito o diagnóstico.
     Sugestões:
     - Enviar link para download (WeTransfer, file.io, etc.)
     - Ou anexar diretamente à issue (se pequena)
-->

- [ ] Vou partilhar amostra (link abaixo)
- [ ] Não posso partilhar, mas o output acima já permite diagnosticar
- [ ] Não posso partilhar e preciso de ajuda para gerar dados de teste sintéticos

## 🌍 Contexto

- **Sistema operativo**: [ex.: Ubuntu 24.04]
- **Versão do Python**: [ex.: 3.12]
- **Versão do Pillow**: [ex.: 10.4.0]
- **Tens `exiftool` instalado?**: [sim / não — `which exiftool`]
- **Tens `exifread` instalado?**: [sim / não — `pip show exifread`]

## 💡 Sugestão de solução (opcional)

<!-- Se és programador e tens uma ideia de como resolver, descreve aqui.
     PRs são bem-vindas! -->
