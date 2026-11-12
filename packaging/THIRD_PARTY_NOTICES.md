# Third-party notices / Avisos de terceros

**[English](#english) · [Español](#español)**

---

<a name="english"></a>
## English

The macOS desktop application of AudioLibro Libre includes, in addition to the project's own code (MIT, see `LICENSE`), the components listed below. **The complete license texts are in the `licenses/` folder inside the application.**

### Programs included in `Contents/Resources/bin/`

| Program | Version | License | How to obtain the source code |
|---|---|---|---|
| **ffmpeg** | see `source-hashes.txt` | **LGPL-2.1 or later** (compiled with `--disable-gpl --disable-nonfree`) | The exact upstream tarball and the build options (`ffmpeg-configure-flags.txt`) are published alongside the installer, on the same release. Original source: <https://ffmpeg.org/download.html> |
| **LAME** (statically linked inside ffmpeg) | 3.100 | **LGPL-2** | Tarball published alongside the installer. Original source: <https://lame.sourceforge.io/> |
| **espeak-ng** | see `source-hashes.txt` | **GPL-3.0 or later** | Tarball published alongside the installer. Original source: <https://github.com/espeak-ng/espeak-ng> |

- ffmpeg and espeak-ng are **independent programs**: AudioLibro Libre runs them as separate processes and is not linked with them. They can be replaced by other copies by placing those first in the `PATH` (or through the `AUDIOLIBRO_ESPEAK` variable).
- To rebuild them: `tools/mac/build_ffmpeg.sh` and `tools/mac/build_espeak.sh` (see `docs/MAC_APP.md`).
- If the source code is not available alongside this version, request it by opening an issue in the project repository.

### Python components packaged with PyInstaller

Python (PSF-2.0), onnxruntime (MIT), numpy (BSD-3), FastAPI, Pydantic and Starlette (MIT), uvicorn (BSD-3), lxml (BSD-3), soundfile and libsndfile (BSD-3 / LGPL-2.1, dynamically linked), pypdf (BSD-3), pypdfium2 and PDFium (BSD-3 / Apache-2.0), python-docx (MIT), Pillow (MIT-CMU), pytesseract (Apache-2.0), httpx (BSD-3), pywebview (BSD-3) and PyObjC (MIT). The list with the license of each voice is in `LICENSES.md`.

The **PyInstaller** packager (GPL-2.0 with a bootloader exception that permits distributing programs under any license) is only a build tool.

### Notice

Users must hold the rights to the books they convert. This application does not include or distribute copyrighted books.

---

<a name="español"></a>
## Español

La aplicación de escritorio de AudioLibro Libre para macOS incluye, además del código propio del proyecto (MIT, véase `LICENSE`), los componentes que se indican a continuación. **Los textos completos de las licencias están en la carpeta `licenses/` dentro de la propia aplicación.**

### Programas incluidos en `Contents/Resources/bin/`

| Programa | Versión | Licencia | Cómo obtener el código fuente |
|---|---|---|---|
| **ffmpeg** | véase `source-hashes.txt` | **LGPL-2.1 o posterior** (compilado con `--disable-gpl --disable-nonfree`) | El tarball oficial exacto y las opciones de compilación (`ffmpeg-configure-flags.txt`) se publican junto al instalador, en la misma versión. Fuente original: <https://ffmpeg.org/download.html> |
| **LAME** (enlazado estáticamente dentro de ffmpeg) | 3.100 | **LGPL-2** | Tarball publicado junto al instalador. Fuente original: <https://lame.sourceforge.io/> |
| **espeak-ng** | véase `source-hashes.txt` | **GPL-3.0 o posterior** | Tarball publicado junto al instalador. Fuente original: <https://github.com/espeak-ng/espeak-ng> |

- ffmpeg y espeak-ng son **programas independientes**: AudioLibro Libre los ejecuta como procesos aparte y no se enlaza con ellos. Pueden sustituirse por otras copias situando estas primero en el `PATH` (o mediante la variable `AUDIOLIBRO_ESPEAK`).
- Para reconstruirlos: `tools/mac/build_ffmpeg.sh` y `tools/mac/build_espeak.sh` (véase `docs/MAC_APP.md`).
- Si el código fuente no está disponible junto a esta versión, solicítelo abriendo una incidencia en el repositorio del proyecto.

### Componentes de Python empaquetados con PyInstaller

Python (PSF-2.0), onnxruntime (MIT), numpy (BSD-3), FastAPI, Pydantic y Starlette (MIT), uvicorn (BSD-3), lxml (BSD-3), soundfile y libsndfile (BSD-3 / LGPL-2.1, enlace dinámico), pypdf (BSD-3), pypdfium2 y PDFium (BSD-3 / Apache-2.0), python-docx (MIT), Pillow (MIT-CMU), pytesseract (Apache-2.0), httpx (BSD-3), pywebview (BSD-3) y PyObjC (MIT). La lista con la licencia de cada voz está en `LICENSES.md`.

El empaquetador **PyInstaller** (GPL-2.0 con una excepción del *bootloader* que permite distribuir programas con cualquier licencia) es solo una herramienta de construcción.

### Aviso

Los usuarios deben tener los derechos de los libros que conviertan. Esta aplicación no incluye ni distribuye libros con copyright.
