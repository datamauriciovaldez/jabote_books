# Licencias / Licenses

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
| `en_GB-alba-medium` | en_GB | medium | CC-BY-4.0 | sí | https://datashare.ed.ac.uk/handle/10283/3270 |
| `en_GB-aru-medium` | en_GB | medium | CC-BY-4.0 | sí | https://www.liverpool.ac.uk/architecture/research/acoustics-research-unit/speech-corpus/ |
| `en_GB-cori-high` | en_GB | high | Public-Domain | no | https://librivox.org |
| `en_GB-cori-medium` | en_GB | medium | CC-BY-4.0 | sí | https://www.openslr.org/109/ |
| `en_GB-vctk-medium` | en_GB | medium | CC-BY-4.0 | sí | https://datashare.ed.ac.uk/handle/10283/3443 |
| `en_US-bryce-medium` | en_US | medium | Public-Domain | no | — |
| `en_US-hifi_tts_92-medium` | en_US | medium | CC-BY-4.0 | sí | https://www.openslr.org/109/ |
| `en_US-joe-medium` | en_US | medium | CC0-1.0 | no | https://github.com/OHF-Voice/voice-datasets |
| `en_US-john-medium` | en_US | medium | Public-Domain | no | https://librivox.org |
| `en_US-kathleen-low` | en_US | low | CC0-1.0 | no | https://github.com/rhasspy/dataset-voice-kathleen |
| `en_US-kristin-medium` | en_US | medium | Public-Domain | no | https://librivox.org |
| `en_US-libritts-high` | en_US | high | CC-BY-4.0 | sí | http://www.openslr.org/60/ |
| `es_ES-carlfm-x_low` | es_ES | x_low | Public-Domain | no | https://github.com/carlfm01/my-speech-datasets |
| `es_ES-davefx-medium` | es_ES | medium | CC0-1.0 | no | https://github.com/OHF-Voice/voice-datasets |
| `es_ES-mls_10246-low` | es_ES | low | CC-BY-4.0 | sí | http://www.openslr.org/94/ |
| `es_ES-mls_9972-low` | es_ES | low | CC-BY-4.0 | sí | http://www.openslr.org/94/ |
| `es_ES-sharvard-medium` | es_ES | medium | CC-BY-3.0 | sí | https://datashare.ed.ac.uk/handle/10283/574 |
| `es_MX-ald-medium` | es_MX | medium | Unlicense | no | https://huggingface.co/datasets/rmcpantoja/Ald_Mexican_Spanish_speech_dataset |
| `es_MX-claude-high` | es_MX | high | Apache-2.0 | sí | https://huggingface.co/spaces/HirCoir/Piper-TTS-Spanish |

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

Voces en español e inglés del catálogo (31 voces; todas Apache-2.0):

| Idioma | Voces |
|---|---|
| Inglés (EE. UU.) | `af_alloy`, `af_aoede`, `af_bella`, `af_heart`, `af_jessica`, `af_kore`, `af_nicole`, `af_nova`, `af_river`, `af_sarah`, `af_sky`, `am_adam`, `am_echo`, `am_eric`, `am_fenrir`, `am_liam`, `am_michael`, `am_onyx`, `am_puck`, `am_santa` |
| Inglés (Reino Unido) | `bf_alice`, `bf_emma`, `bf_isabella`, `bf_lily`, `bm_daniel`, `bm_fable`, `bm_george`, `bm_lewis` |
| Español | `ef_dora`, `em_alex`, `em_santa` |

## App de escritorio para macOS (opcional)

El instalador `.dmg` (ver `docs/MAC_APP.md`) **redistribuye** estos programas, además del código del proyecto (MIT):

| Componente | Licencia | Notas |
|---|---|---|
| ffmpeg (compilado con `--disable-gpl --disable-nonfree`) | LGPL-2.1+ | programa independiente; el código fuente exacto se publica junto al `.dmg` |
| LAME (dentro de ffmpeg, estático) | LGPL-2 | ídem |
| **espeak-ng** | **GPL-3.0+** | programa independiente, no enlazado; el código fuente se publica junto al `.dmg` |
| PyInstaller (solo al construir) | GPL-2.0+ con excepción del *bootloader* | permite distribuir programas con cualquier licencia |
| pywebview | BSD-3-Clause | ventana nativa |
| PyObjC | MIT | dependencia de pywebview en macOS |

Detalle y obligaciones: `packaging/THIRD_PARTY_NOTICES.md`.

Para regenerar el catálogo: `python tools/audit_voices.py > app/tts/voices.json` y luego
`python tools/gen_licenses.py > LICENSES.md`.

## Aviso legal

Debes tener los derechos del libro que conviertes. Esta herramienta no incluye ni distribuye libros con
copyright. Los libros de ejemplo (`app/samples/`) son fragmentos de dominio público (Cervantes, Austen).

