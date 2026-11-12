# Licenses / Licencias

**[English](#english) · [Español](#español)**

---

<a name="english"></a>
## English

AudioLibro Libre is **MIT**-licensed (see `LICENSE`). This file documents every dependency and every voice.
Project rule: only free, local components with a permissive license suitable for commercial use.
Verified against PyPI and Hugging Face on 2026-11-12 (details and rejected components in `docs/DECISIONS.md`).

### Python dependencies

| Package | License | Purpose |
|---|---|---|
| fastapi, pydantic | MIT | Web API |
| uvicorn | BSD-3-Clause | Server |
| python-multipart | Apache-2.0 | File uploads |
| httpx | BSD-3-Clause | Voice downloads |
| numpy | BSD-3-Clause (and other permissive licenses) | Audio |
| onnxruntime | MIT | Inference for the voice models |
| soundfile | BSD-3-Clause | Audio reading and writing (libsndfile is LGPL, dynamically linked) |
| lxml | BSD-3-Clause | EPUB |
| beautifulsoup4 | MIT | HTML utilities |
| pypdf | BSD-3-Clause | Text-based PDF |
| pypdfium2 | BSD-3-Clause / Apache-2.0 (includes PDFium, BSD-3) | Page rendering for OCR |
| python-docx | MIT | Word (.docx) |
| pytesseract | Apache-2.0 | Bridge to Tesseract |
| Pillow | MIT-CMU (HPND, permissive) | Images for OCR |
| pytest, ruff (development) | MIT | Tests and style |

**Rejected on purpose:** `ebooklib` (AGPL-3.0), `pymupdf` (AGPL-3.0), `mutagen` (GPL-2.0+),
`piper-tts` >= 1.3 (GPL-3.0) and `kokoro-onnx` / `phonemizer` (they pull in GPL-3.0).

### External programs (not included in the repository; invoked from the command line)

| Program | License | Purpose | Note |
|---|---|---|---|
| ffmpeg | LGPL-2.1+ / GPL depending on the build | MP3, normalization, metadata | Separate program; neither linked nor redistributed here |
| **espeak-ng** | **GPL-3.0** | Converting text into phonemes | **The only exception to the "permissive" criterion.** It is executed as a separate process and never linked. The generated audio is not subject to the GPL. It can be replaced through the `TTSEngine` interface |
| Tesseract (optional) | Apache-2.0 | OCR for scanned PDFs | If missing, the application explains how to install it |

### Piper engine

The inference code in `app/tts/piper.py` is original (MIT) and uses the `.onnx` models from
[rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices) (MIT repository). **Each voice carries the
license of its training data**; only voices on this allow-list are offered: CC0, public domain,
Unlicense, MIT, Apache-2.0 and CC-BY (with attribution). CC-BY-SA, non-commercial and unspecified licenses are excluded.
Any required attribution is added automatically to `CREDITOS.txt` inside the exported ZIP.

#### Voices in the catalog

| Voice | Locale | Quality | Data license | Attribution | Data source |
|---|---|---|---|---|---|
| `en_GB-alba-medium` | en_GB | medium | CC-BY-4.0 | yes | https://datashare.ed.ac.uk/handle/10283/3270 |
| `en_GB-aru-medium` | en_GB | medium | CC-BY-4.0 | yes | https://www.liverpool.ac.uk/architecture/research/acoustics-research-unit/speech-corpus/ |
| `en_GB-cori-high` | en_GB | high | Public-Domain | no | https://librivox.org |
| `en_GB-cori-medium` | en_GB | medium | CC-BY-4.0 | yes | https://www.openslr.org/109/ |
| `en_GB-vctk-medium` | en_GB | medium | CC-BY-4.0 | yes | https://datashare.ed.ac.uk/handle/10283/3443 |
| `en_US-bryce-medium` | en_US | medium | Public-Domain | no | — |
| `en_US-hifi_tts_92-medium` | en_US | medium | CC-BY-4.0 | yes | https://www.openslr.org/109/ |
| `en_US-joe-medium` | en_US | medium | CC0-1.0 | no | https://github.com/OHF-Voice/voice-datasets |
| `en_US-john-medium` | en_US | medium | Public-Domain | no | https://librivox.org |
| `en_US-kathleen-low` | en_US | low | CC0-1.0 | no | https://github.com/rhasspy/dataset-voice-kathleen |
| `en_US-kristin-medium` | en_US | medium | Public-Domain | no | https://librivox.org |
| `en_US-libritts-high` | en_US | high | CC-BY-4.0 | yes | http://www.openslr.org/60/ |
| `es_ES-carlfm-x_low` | es_ES | x_low | Public-Domain | no | https://github.com/carlfm01/my-speech-datasets |
| `es_ES-davefx-medium` | es_ES | medium | CC0-1.0 | no | https://github.com/OHF-Voice/voice-datasets |
| `es_ES-mls_10246-low` | es_ES | low | CC-BY-4.0 | yes | http://www.openslr.org/94/ |
| `es_ES-mls_9972-low` | es_ES | low | CC-BY-4.0 | yes | http://www.openslr.org/94/ |
| `es_ES-sharvard-medium` | es_ES | medium | CC-BY-3.0 | yes | https://datashare.ed.ac.uk/handle/10283/574 |
| `es_MX-ald-medium` | es_MX | medium | Unlicense | no | https://huggingface.co/datasets/rmcpantoja/Ald_Mexican_Spanish_speech_dataset |
| `es_MX-claude-high` | es_MX | high | Apache-2.0 | yes | https://huggingface.co/spaces/HirCoir/Piper-TTS-Spanish |

### Kokoro engine (optional)

The [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) model by hexgrad, in its ONNX form from
[onnx-community/Kokoro-82M-v1.0-ONNX](https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX).
**License of the weights and voices: Apache-2.0** (checked on the official model card of both repositories by
`tools/audit_kokoro.py`, which refuses to generate the catalog if it changes). `model.onnx` is used (fp32, 326 MB): the
int8 variant was slower on CPU.

Inference is original code (`app/tts/kokoro.py`, MIT) using `onnxruntime` and an external espeak-ng. The `kokoro-onnx` and
`phonemizer` packages (GPL-3) are **not used**. The symbol vocabulary (`app/tts/kokoro_vocab.json`, 114 entries) comes from the
official `config.json` (Apache-2.0).

**Training data** (according to the official README): permissive or copyright-free audio (Apache, MIT and similar) and
synthetic audio from closed providers; also CC BY audio (for example SIWIS and Koniwa, which do not correspond to
Spanish or English voices). The full attribution is in the model's README.

Spanish and English voices in the catalog (31 voices; all Apache-2.0):

| Language | Voices |
|---|---|
| English (US) | `af_alloy`, `af_aoede`, `af_bella`, `af_heart`, `af_jessica`, `af_kore`, `af_nicole`, `af_nova`, `af_river`, `af_sarah`, `af_sky`, `am_adam`, `am_echo`, `am_eric`, `am_fenrir`, `am_liam`, `am_michael`, `am_onyx`, `am_puck`, `am_santa` |
| English (UK) | `bf_alice`, `bf_emma`, `bf_isabella`, `bf_lily`, `bm_daniel`, `bm_fable`, `bm_george`, `bm_lewis` |
| Spanish | `ef_dora`, `em_alex`, `em_santa` |

### Desktop application for macOS (optional)

The `.dmg` installer (see `docs/MAC_APP.md`) **redistributes** the following programs, in addition to the project's code (MIT):

| Component | License | Notes |
|---|---|---|
| ffmpeg (compiled with `--disable-gpl --disable-nonfree`) | LGPL-2.1+ | independent program; the exact source code is published alongside the `.dmg` |
| LAME (inside ffmpeg, static) | LGPL-2 | same |
| **espeak-ng** | **GPL-3.0+** | independent program, not linked; the source code is published alongside the `.dmg` |
| PyInstaller (build time only) | GPL-2.0+ with a bootloader exception | permits distributing programs under any license |
| pywebview | BSD-3-Clause | native window |
| PyObjC | MIT | pywebview dependency on macOS |

Details and obligations: `packaging/THIRD_PARTY_NOTICES.md`.

To regenerate the catalogs: `python tools/audit_voices.py > app/tts/voices.json` and then
`python tools/gen_licenses.py > LICENSES.md`.

### Legal notice

Users must hold the rights to the books they convert. This software does not include or distribute copyrighted books.
The sample books (`app/samples/`) are public-domain excerpts (Cervantes and Austen).

---

<a name="español"></a>
## Español

AudioLibro Libre tiene licencia **MIT** (véase `LICENSE`). Este archivo documenta cada dependencia y cada voz.
Regla del proyecto: solo componentes gratuitos y locales con una licencia permisiva apta para el uso comercial.
Verificado contra PyPI y Hugging Face el 2026-11-12 (detalles y componentes descartados en `docs/DECISIONS.md`).

### Dependencias de Python

| Paquete | Licencia | Uso |
|---|---|---|
| fastapi, pydantic | MIT | API web |
| uvicorn | BSD-3-Clause | Servidor |
| python-multipart | Apache-2.0 | Subida de archivos |
| httpx | BSD-3-Clause | Descarga de voces |
| numpy | BSD-3-Clause (y otras permisivas) | Audio |
| onnxruntime | MIT | Inferencia de los modelos de voz |
| soundfile | BSD-3-Clause | Lectura y escritura de audio (libsndfile es LGPL, enlace dinámico) |
| lxml | BSD-3-Clause | EPUB |
| beautifulsoup4 | MIT | Utilidades de HTML |
| pypdf | BSD-3-Clause | PDF con texto |
| pypdfium2 | BSD-3-Clause / Apache-2.0 (incluye PDFium, BSD-3) | Renderizado de páginas para OCR |
| python-docx | MIT | Word (.docx) |
| pytesseract | Apache-2.0 | Interfaz con Tesseract |
| Pillow | MIT-CMU (HPND, permisiva) | Imágenes para OCR |
| pytest, ruff (desarrollo) | MIT | Pruebas y estilo |

**Descartadas deliberadamente:** `ebooklib` (AGPL-3.0), `pymupdf` (AGPL-3.0), `mutagen` (GPL-2.0+),
`piper-tts` >= 1.3 (GPL-3.0) y `kokoro-onnx` / `phonemizer` (arrastran GPL-3.0).

### Programas externos (no se incluyen en el repositorio; se invocan por línea de comandos)

| Programa | Licencia | Uso | Nota |
|---|---|---|---|
| ffmpeg | LGPL-2.1+ / GPL según la compilación | MP3, normalización, metadatos | Programa independiente; no se enlaza ni se redistribuye aquí |
| **espeak-ng** | **GPL-3.0** | Conversión de texto en fonemas | **Única excepción al criterio «permisivo».** Se ejecuta como proceso independiente y nunca se enlaza. El audio generado no queda sujeto a la GPL. Puede sustituirse mediante la interfaz `TTSEngine` |
| Tesseract (opcional) | Apache-2.0 | OCR de PDF escaneados | Si falta, la aplicación explica cómo instalarlo |

### Motor Piper

El código de inferencia de `app/tts/piper.py` es propio (MIT) y utiliza los modelos `.onnx` de
[rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices) (repositorio MIT). **Cada voz tiene la
licencia de sus datos de entrenamiento**; solo se ofrecen las de esta lista blanca: CC0, dominio público,
Unlicense, MIT, Apache-2.0 y CC-BY (con atribución). Se excluyen CC-BY-SA, las licencias no comerciales y las no
especificadas. La atribución exigida se incluye automáticamente en `CREDITOS.txt` dentro del ZIP exportado.

#### Voces incluidas en el catálogo

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

### Motor Kokoro (opcional)

El modelo [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) de hexgrad, en su versión ONNX de
[onnx-community/Kokoro-82M-v1.0-ONNX](https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX).
**Licencia de los pesos y de las voces: Apache-2.0** (comprobada en la ficha oficial de ambos repositorios por
`tools/audit_kokoro.py`, que se niega a generar el catálogo si cambia). Se utiliza `model.onnx` (fp32, 326 MB): la variante
int8 resultó más lenta en CPU.

La inferencia es código propio (`app/tts/kokoro.py`, MIT) con `onnxruntime` y un espeak-ng externo. **No se usan** los paquetes
`kokoro-onnx` ni `phonemizer` (GPL-3). El vocabulario de símbolos (`app/tts/kokoro_vocab.json`, 114 entradas) procede del
`config.json` oficial (Apache-2.0).

**Datos de entrenamiento** (según el README oficial): audio permisivo o sin copyright (Apache, MIT y similares) y
audio sintético de proveedores cerrados; también audio CC BY (por ejemplo, SIWIS y Koniwa, que no corresponden a voces
en español ni en inglés). La atribución completa figura en el README del modelo.

Voces en español e inglés del catálogo (31 voces; todas Apache-2.0):

| Idioma | Voces |
|---|---|
| Inglés (EE. UU.) | `af_alloy`, `af_aoede`, `af_bella`, `af_heart`, `af_jessica`, `af_kore`, `af_nicole`, `af_nova`, `af_river`, `af_sarah`, `af_sky`, `am_adam`, `am_echo`, `am_eric`, `am_fenrir`, `am_liam`, `am_michael`, `am_onyx`, `am_puck`, `am_santa` |
| Inglés (Reino Unido) | `bf_alice`, `bf_emma`, `bf_isabella`, `bf_lily`, `bm_daniel`, `bm_fable`, `bm_george`, `bm_lewis` |
| Español | `ef_dora`, `em_alex`, `em_santa` |

### Aplicación de escritorio para macOS (opcional)

El instalador `.dmg` (véase `docs/MAC_APP.md`) **redistribuye** los siguientes programas, además del código del proyecto (MIT):

| Componente | Licencia | Notas |
|---|---|---|
| ffmpeg (compilado con `--disable-gpl --disable-nonfree`) | LGPL-2.1+ | programa independiente; el código fuente exacto se publica junto al `.dmg` |
| LAME (dentro de ffmpeg, estático) | LGPL-2 | ídem |
| **espeak-ng** | **GPL-3.0+** | programa independiente, no enlazado; el código fuente se publica junto al `.dmg` |
| PyInstaller (solo al construir) | GPL-2.0+ con excepción del *bootloader* | permite distribuir programas con cualquier licencia |
| pywebview | BSD-3-Clause | ventana nativa |
| PyObjC | MIT | dependencia de pywebview en macOS |

Detalles y obligaciones: `packaging/THIRD_PARTY_NOTICES.md`.

Para regenerar los catálogos: `python tools/audit_voices.py > app/tts/voices.json` y después
`python tools/gen_licenses.py > LICENSES.md`.

### Aviso legal

Los usuarios deben tener los derechos de los libros que conviertan. Este software no incluye ni distribuye libros con
copyright. Los libros de ejemplo (`app/samples/`) son fragmentos de dominio público (Cervantes y Austen).

