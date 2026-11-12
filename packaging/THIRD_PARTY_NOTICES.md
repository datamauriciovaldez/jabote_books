# Avisos de terceros / Third-party notices

La app de escritorio de AudioLibro Libre (macOS) incluye, además del código del proyecto (MIT, ver `LICENSE`),
los siguientes componentes. **Las licencias completas están en la carpeta `licenses/` de la propia app.**

## Programas incluidos en `Contents/Resources/bin/`

| Programa | Versión | Licencia | Cómo obtener el código fuente |
|---|---|---|---|
| **ffmpeg** | ver `source-hashes.txt` | **LGPL-2.1 o posterior** (compilado con `--disable-gpl --disable-nonfree`) | El tarball oficial exacto y las opciones de compilación (`ffmpeg-configure-flags.txt`) se publican junto al instalador, en la misma *release*. Fuente original: <https://ffmpeg.org/download.html> |
| **LAME** (dentro de ffmpeg, estático) | 3.100 | **LGPL-2** | Tarball publicado junto al instalador. Fuente original: <https://lame.sourceforge.io/> |
| **espeak-ng** | ver `source-hashes.txt` | **GPL-3.0 o posterior** | Tarball publicado junto al instalador. Fuente original: <https://github.com/espeak-ng/espeak-ng> |

- ffmpeg y espeak-ng son **programas independientes**: AudioLibro Libre los ejecuta como procesos aparte y no se
  enlaza con ellos. Pueden sustituirse por otras copias poniendo las suyas antes en el `PATH` (o con la variable
  `AUDIOLIBRO_ESPEAK`).
- Para reconstruirlos: `tools/mac/build_ffmpeg.sh` y `tools/mac/build_espeak.sh` (ver `docs/MAC_APP.md`).
- Si no encuentras el código fuente junto a esta versión, pídelo abriendo una *issue* en el repositorio del proyecto.

## Componentes de Python empaquetados (PyInstaller)

Python (PSF-2.0), onnxruntime (MIT), numpy (BSD-3), FastAPI/Pydantic/Starlette (MIT), uvicorn (BSD-3),
lxml (BSD-3), soundfile y libsndfile (BSD-3 / LGPL-2.1, enlace dinámico), pypdf (BSD-3), pypdfium2 y PDFium
(BSD-3 / Apache-2.0), python-docx (MIT), Pillow (MIT-CMU), pytesseract (Apache-2.0), httpx (BSD-3),
pywebview (BSD-3) y PyObjC (MIT). La lista con las licencias de cada voz está en `LICENSES.md`.

El empaquetador **PyInstaller** (GPL-2.0 con excepción del *bootloader*, que permite distribuir programas con
cualquier licencia) es solo una herramienta de construcción.

## Aviso

Debes tener los derechos de los libros que conviertas. Esta aplicación no incluye ni distribuye libros con copyright.
