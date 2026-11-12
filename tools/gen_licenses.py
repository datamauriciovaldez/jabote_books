"""Genera LICENSES.md a partir de app/tts/voices.json (así las voces nunca quedan desactualizadas).

Uso:  python tools/gen_licenses.py > LICENSES.md
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

HEAD = """# Licencias / Licenses

AudioLibro Libre es **MIT** (ver `LICENSE`). Este archivo documenta cada dependencia y cada voz.
Regla del proyecto: solo componentes gratuitos, locales y con licencia permisiva apta para uso comercial.
Verificado contra PyPI y Hugging Face el 2026-11-12 (detalle y descartes en `docs/DECISIONS.md`).

## Dependencias de Python

| Paquete | Licencia | Uso |
|---|---|---|
| fastapi, pydantic | MIT | API web |
| uvicorn | BSD-3-Clause | Servidor |
| python-multipart | Apache-2.0 | Subida de archivos |
| httpx | BSD-3-Clause | Descarga de voces |
| numpy | BSD-3-Clause (y otras permisivas) | Audio |
| onnxruntime | MIT | Inferencia de los modelos de voz |
| soundfile | BSD-3-Clause | Lectura/escritura de audio (libsndfile es LGPL, enlace dinámico) |
| lxml | BSD-3-Clause | EPUB |
| beautifulsoup4 | MIT | Utilidades de HTML |
| pypdf | BSD-3-Clause | PDF con texto |
| pypdfium2 | BSD-3-Clause / Apache-2.0 (incluye PDFium, BSD-3) | Renderizar páginas para OCR |
| python-docx | MIT | Word (.docx) |
| pytesseract | Apache-2.0 | Puente hacia Tesseract |
| Pillow | MIT-CMU (HPND, permisiva) | Imágenes para OCR |
| pytest, ruff (desarrollo) | MIT | Pruebas y estilo |

**Descartadas a propósito:** `ebooklib` (AGPL-3.0), `pymupdf` (AGPL-3.0), `mutagen` (GPL-2.0+),
`piper-tts` >= 1.3 (GPL-3.0) y `kokoro-onnx`/`phonemizer` (arrastran GPL-3.0).

## Programas externos (no se incluyen en el repositorio; se llaman por línea de comandos)

| Programa | Licencia | Uso | Nota |
|---|---|---|---|
| ffmpeg | LGPL-2.1+ / GPL según la compilación | MP3, normalización, metadatos | Programa separado; no se enlaza ni se redistribuye aquí |
| **espeak-ng** | **GPL-3.0** | Convertir texto en fonemas | **Única excepción al criterio "permisivo".** Se ejecuta como proceso aparte, sin enlazar. El audio generado no queda sujeto a la GPL. Sustituible mediante la interfaz `TTSEngine` |
| Tesseract (opcional) | Apache-2.0 | OCR de PDFs escaneados | Si falta, la app avisa con instrucciones |

## Motor Piper

El código de inferencia de `app/tts/piper.py` es propio (MIT) y usa los modelos `.onnx` de
[rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices) (repositorio MIT). **Cada voz tiene la
licencia de sus datos de entrenamiento**; solo se ofrecen las de esta lista blanca: CC0, dominio público,
Unlicense, MIT, Apache-2.0 y CC-BY (con atribución). Se excluyen CC-BY-SA, no comerciales y las de licencia
no especificada. La atribución exigida se incluye automáticamente en `CREDITOS.txt` dentro del ZIP exportado.

### Voces incluidas en el catálogo

| Voz | Idioma | Calidad | Licencia de los datos | Atribución | Origen de los datos |
|---|---|---|---|---|---|
"""

KOKORO_HEAD = """
## Motor Kokoro (opcional)

Modelo [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) de hexgrad, en su versión ONNX de
[onnx-community/Kokoro-82M-v1.0-ONNX](https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX).
**Licencia de los pesos y de las voces: Apache-2.0** (comprobada en la ficha oficial de ambos repositorios por
`tools/audit_kokoro.py`, que se niega a generar el catálogo si cambia). Se usa `model.onnx` (fp32, 326 MB): la variante
int8 resultó más lenta en CPU.

Inferencia propia (`app/tts/kokoro.py`, MIT) con `onnxruntime` y espeak-ng externo. **No se usan** los paquetes
`kokoro-onnx` ni `phonemizer` (GPL-3). El vocabulario de símbolos (`app/tts/kokoro_vocab.json`, 114 entradas) procede del
`config.json` oficial (Apache-2.0).

**Datos de entrenamiento** (según el README oficial): audio permisivo o no protegido por copyright (Apache, MIT, etc.) y
audio sintético de proveedores cerrados; también audio CC BY (p. ej. SIWIS y Koniwa, que no corresponden a voces
en español ni en inglés). La atribución completa está en el README del modelo.

Voces en español e inglés del catálogo ({n} voces; todas Apache-2.0):

| Idioma | Voces |
|---|---|
{rows}
"""

FOOT = """
Para regenerar el catálogo: `python tools/audit_voices.py > app/tts/voices.json` y luego
`python tools/gen_licenses.py > LICENSES.md`.

## Aviso legal

Debes tener los derechos del libro que conviertes. Esta herramienta no incluye ni distribuye libros con
copyright. Los libros de ejemplo (`app/samples/`) son fragmentos de dominio público (Cervantes, Austen).
"""


def kokoro_section() -> str:
    cat = json.loads((ROOT / "app/tts/kokoro_voices.json").read_text(encoding="utf-8"))
    groups: dict[str, list[str]] = {}
    for v in cat["voices"]:
        groups.setdefault(v["locale"], []).append(v["id"])
    labels = {"es": "Español", "en_US": "Inglés (EE. UU.)", "en_GB": "Inglés (Reino Unido)"}
    rows = "\n".join(f"| {labels[k]} | {', '.join(f'`{i}`' for i in ids)} |" for k, ids in groups.items())
    return KOKORO_HEAD.replace("{n}", str(len(cat["voices"]))).replace("{rows}", rows)


def main() -> None:
    voices = json.loads((ROOT / "app/tts/voices.json").read_text(encoding="utf-8"))["voices"]
    rows = []
    for v in sorted(voices, key=lambda x: (x["lang"], x["id"])):
        rows.append(f"| `{v['id']}` | {v['locale']} | {v['quality']} | {v['license']} | "
                    f"{'sí' if v['attribution_required'] else 'no'} | {v['dataset_url'] or '—'} |")
    print(HEAD + "\n".join(rows) + "\n" + kokoro_section() + FOOT)


if __name__ == "__main__":
    main()
