# Troubleshooting / Solución de problemas

**[English](#english) · [Español](#español)**

---

<a name="english"></a>
## English

When the application displays a red "Something went wrong" box, read its **"What you can do"** line first: it resolves most problems. This guide covers the most common cases in more detail.

### 1. Viewing logs and diagnostics

| How the application is run | Where to look |
|---|---|
| Docker | `docker compose logs -f` (Ctrl+C to exit), or the *Logs* tab of the container in Docker Desktop |
| `install.bat` / `install.sh` | The terminal window itself |
| Dependency installation failure | `.venv/install.log` |
| Any method | `http://localhost:8000/api/system` reports whether ffmpeg, espeak-ng and Tesseract are available |

### 2. The application does not start or does not open

**Docker**
- *"Cannot connect to the Docker daemon"* or Docker does not start: open Docker Desktop and wait until it reports "Running". On Windows, Docker Desktop requires **WSL 2** and **virtualization enabled in the BIOS/UEFI**; if that is not possible, use `install.bat` instead.
- *Port 8000 is already allocated* (`port is already allocated`): in `docker-compose.yml`, change `"127.0.0.1:8000:8000"` to `"127.0.0.1:8080:8000"` and open <http://localhost:8080>.
- *Access from another device on the local network:* for security, the application listens only on the local machine (`127.0.0.1`). If remote access is genuinely required, change the mapping to `"8000:8000"`, bearing in mind that any device on the network will then be able to use the application.
- *Slow first run:* building the image downloads roughly 1 GB (Python, ffmpeg, Tesseract). This happens once.

**Without Docker**
- *"Python 3.10 or later was not found":* install Python from <https://www.python.org/downloads/> (on Windows, select **"Add python.exe to PATH"**).
- *`No module named venv`* (Debian/Ubuntu): `sudo apt install python3-venv`.
- *Dependency installation failed:* this is almost always a connectivity problem. Review `.venv/install.log` and run the installer again.
- Windows: if `install.bat` closes immediately, start it from a `cmd` window to read the message.

### 3. Missing external programs

| Program | Purpose | Windows | macOS | Linux |
|---|---|---|---|---|
| **ffmpeg** | MP3/M4B creation | `winget install Gyan.FFmpeg` | `brew install ffmpeg` | `sudo apt install ffmpeg` |
| **espeak-ng** | pronunciation | `.msi` installer from <https://github.com/espeak-ng/espeak-ng/releases> | `brew install espeak-ng` | `sudo apt install espeak-ng` |
| **Tesseract** (optional) | OCR for scanned PDFs | <https://github.com/UB-Mannheim/tesseract/wiki> (select the Spanish language data) | `brew install tesseract tesseract-lang` | `sudo apt install tesseract-ocr tesseract-ocr-spa` |

After installing them, **close and reopen** the application. If espeak-ng is installed but not detected, set its path in the `AUDIOLIBRO_ESPEAK` environment variable (for example, `C:\Program Files\eSpeak NG\espeak-ng.exe`). On Windows, the installer's default locations are also searched.

### 4. Voices

- **"Could not connect to download the voice":** internet access is required **only** for this step. Behind a proxy or firewall, allow `huggingface.co`.
- **"The voice file downloaded incomplete or damaged":** select "Download voice" again. Every download is verified with SHA-256.
- **Manual installation** (when the machine cannot reach the download host): on another computer, download the two Piper voice files (`<id>.onnx` and `<id>.onnx.json`) from `huggingface.co/rhasspy/piper-voices` and copy them to `data/voices/`. For Kokoro, place `model.onnx` and `<voice>.bin` from `onnx-community/Kokoro-82M-v1.0-ONNX` in `data/voices/kokoro/`.
- **A voice sounds robotic or drops words:** try another voice (*medium* and *high* quality sound better than *low* and *basic*) or Kokoro (more natural, but slower).

### 5. The book

- **EPUB with DRM:** cannot be read. Use an unprotected copy of a book you hold the rights to.
- **Multi-column or heavily formatted PDF:** the text may be out of order. Review it in step 2 or convert the file to EPUB or TXT first.
- **Scanned PDF:** processed with OCR (requires Tesseract). A 300-page book takes about five minutes; keep the tab open.
- **Chapters detected incorrectly:** in step 2 you can rename, add, remove and untick chapters and edit the text. If a TXT file does not mark chapters, add lines such as `Chapter 1` separated by a blank line.
- **Unexpected characters in a TXT file:** save the file with UTF-8 encoding.
- **The index or acknowledgements are narrated:** untick those chapters in step 2.

### 6. Pronunciation

In step 3, open the **pronunciation dictionary** and enter, in the right-hand column, how the word should sound (spelled phonetically): `WiFi` to `guai fai`, `UN` to `you en`, `Hermione` to `her-my-oh-nee`. The dictionary applies to the whole book and regenerates only the affected fragments. Use the **10-second sample** to test a rule.

### 7. Performance, memory and disk

- **Generation is slow:** use **Piper** (roughly 25 times faster than Kokoro), close other applications and consult the estimate in step 3, which is measured on your machine. Older laptops may be two to five times slower than the measurements in the README.
- **Low memory:** Piper uses about 0.6 GB and Kokoro about 1.1 GB; long books do not increase memory use because they are processed in fragments.
- **Disk full:** an eight-hour book occupies about 1.6 GB (about 2.7 GB during export). Delete old projects under "My projects".
- **The M4B does not play correctly:** use the MP3 files. The M4B is 64 kbps mono AAC with chapter markers; if an application does not show the chapters, try VLC, Apple Books or Audiobookshelf.

### 8. Data location and maintenance

- **Docker:** voices, projects and audio are stored in the `audiolibro-data` volume (list volumes with `docker volume ls`; the name is prefixed with the folder name). Backup: `docker cp audiolibro-libre:/data ./audiolibro-backup`.
- **Without Docker:** the `data/` folder next to the project (or the folder set in `AUDIOLIBRO_DATA`).
- **Stop without deleting anything:** `docker compose down`. **Delete everything** (including voices and projects): `docker compose down -v`.
- **Update:** download the new version, replace the files and run `docker compose up -d --build` (data is preserved). Without Docker, run the installer again.

### 9. The application closed during generation

No work is lost: each fragment is saved when it finishes. Open the application, go to "My projects", open the project and select **Resume**. Only the missing fragments are generated.

### 10. Reporting a defect

Open an issue that includes: operating system, how the application is run (Docker, scripts or Colab), the **exact text** of the red error box, the output of `http://localhost:8000/api/system` and, if possible, the last lines of the log (section 1). **Do not attach copyrighted books.**

---

<a name="español"></a>
## Español

Cuando la aplicación muestre un cuadro rojo «Algo no ha ido bien», lea primero la línea **«Qué puedes hacer»** (el texto exacto de la interfaz): resuelve la mayoría de los problemas. Esta guía describe con más detalle los casos más habituales.

### 1. Consulta de registros y diagnóstico

| Forma de ejecución | Dónde consultar |
|---|---|
| Docker | `docker compose logs -f` (Ctrl+C para salir) o la pestaña *Logs* del contenedor en Docker Desktop |
| `install.bat` / `install.sh` | La propia ventana de la terminal |
| Fallo al instalar dependencias | `.venv/install.log` |
| Cualquiera | `http://localhost:8000/api/system` indica si ffmpeg, espeak-ng y Tesseract están disponibles |

### 2. La aplicación no arranca o no se abre

**Docker**
- *«Cannot connect to the Docker daemon»* o Docker no se inicia: abra Docker Desktop y espere a que indique «Running». En Windows, Docker Desktop requiere **WSL 2** y la **virtualización activada en la BIOS/UEFI**; si no es posible, utilice `install.bat`.
- *Puerto 8000 ocupado* (`port is already allocated`): en `docker-compose.yml`, cambie `"127.0.0.1:8000:8000"` por `"127.0.0.1:8080:8000"` y abra <http://localhost:8080>.
- *Acceso desde otro dispositivo de la red local:* por seguridad, la aplicación solo escucha en la propia máquina (`127.0.0.1`). Si el acceso remoto es realmente necesario, cambie la asignación a `"8000:8000"`, teniendo en cuenta que cualquier dispositivo de la red podrá usar la aplicación.
- *Primera ejecución lenta:* construir la imagen descarga aproximadamente 1 GB (Python, ffmpeg, Tesseract). Ocurre una sola vez.

**Sin Docker**
- *«No se ha encontrado Python 3.10 o superior»:* instale Python desde <https://www.python.org/downloads/> (en Windows, marque **«Add python.exe to PATH»**).
- *`No module named venv`* (Debian/Ubuntu): `sudo apt install python3-venv`.
- *Falló la instalación de dependencias:* casi siempre se debe a la conexión. Revise `.venv/install.log` y vuelva a ejecutar el instalador.
- Windows: si `install.bat` se cierra inmediatamente, ejecútelo desde una ventana `cmd` para ver el mensaje.

### 3. Programas externos ausentes

| Programa | Finalidad | Windows | macOS | Linux |
|---|---|---|---|---|
| **ffmpeg** | creación de MP3/M4B | `winget install Gyan.FFmpeg` | `brew install ffmpeg` | `sudo apt install ffmpeg` |
| **espeak-ng** | pronunciación | instalador `.msi` de <https://github.com/espeak-ng/espeak-ng/releases> | `brew install espeak-ng` | `sudo apt install espeak-ng` |
| **Tesseract** (opcional) | OCR de PDF escaneados | <https://github.com/UB-Mannheim/tesseract/wiki> (seleccione los datos del idioma español) | `brew install tesseract tesseract-lang` | `sudo apt install tesseract-ocr tesseract-ocr-spa` |

Tras instalarlos, **cierre y vuelva a abrir** la aplicación. Si espeak-ng está instalado pero no se detecta, indique su ruta en la variable de entorno `AUDIOLIBRO_ESPEAK` (por ejemplo, `C:\Program Files\eSpeak NG\espeak-ng.exe`). En Windows también se buscan las ubicaciones habituales del instalador.

### 4. Voces

- **«No se ha podido conectar para descargar la voz»:** solo este paso requiere acceso a internet. Detrás de un proxy o cortafuegos, permita `huggingface.co`.
- **«El archivo de la voz se descargó incompleto o dañado»:** seleccione «Descargar voz» de nuevo. Cada descarga se verifica con SHA-256.
- **Instalación manual** (cuando la máquina no puede acceder al servidor de descarga): en otro ordenador, descargue los dos archivos de la voz de Piper (`<id>.onnx` y `<id>.onnx.json`) desde `huggingface.co/rhasspy/piper-voices` y cópielos a `data/voices/`. Para Kokoro, coloque `model.onnx` y `<voz>.bin` de `onnx-community/Kokoro-82M-v1.0-ONNX` en `data/voices/kokoro/`.
- **Una voz suena robótica o pierde palabras:** pruebe otra voz (las de calidad *media* y *alta* suenan mejor que las de calidad *baja* y *básica*) o Kokoro (más natural, pero más lento).

### 5. El libro

- **EPUB con DRM:** no se puede leer. Utilice una copia sin protección de un libro sobre el que tenga derechos.
- **PDF de varias columnas o con mucho formato:** el texto puede quedar desordenado. Revíselo en el paso 2 o convierta antes el archivo a EPUB o TXT.
- **PDF escaneado:** se procesa con OCR (requiere Tesseract). Un libro de 300 páginas tarda unos cinco minutos; mantenga abierta la pestaña.
- **Capítulos detectados incorrectamente:** en el paso 2 se pueden renombrar, añadir, quitar y desmarcar capítulos y editar el texto. Si un archivo TXT no marca los capítulos, añada líneas como `Capítulo 1` separadas por una línea en blanco.
- **Caracteres inesperados en un archivo TXT:** guarde el archivo con codificación UTF-8.
- **Se narran el índice o los agradecimientos:** desmarque esos capítulos en el paso 2.

### 6. Pronunciación

En el paso 3, abra el **diccionario de pronunciación** e introduzca, en la columna derecha, cómo debe sonar la palabra (escrita fonéticamente): `WiFi` a `guai fai`, `ONU` a `onu`, `Hermione` a `Jermaione`. El diccionario se aplica a todo el libro y regenera únicamente los fragmentos afectados. Utilice la **muestra de 10 segundos** para probar una regla.

### 7. Rendimiento, memoria y disco

- **La generación es lenta:** utilice **Piper** (aproximadamente 25 veces más rápido que Kokoro), cierre otras aplicaciones y consulte la estimación del paso 3, que se mide en su equipo. Un portátil antiguo puede ser entre dos y cinco veces más lento que las mediciones del README.
- **Poca memoria:** Piper utiliza unos 0,6 GB y Kokoro unos 1,1 GB; los libros largos no aumentan el uso de memoria porque se procesan por fragmentos.
- **Disco lleno:** un libro de ocho horas ocupa unos 1,6 GB (unos 2,7 GB durante la exportación). Elimine proyectos antiguos en «Mis proyectos».
- **El M4B no se reproduce correctamente:** utilice los MP3. El M4B es AAC mono de 64 kbps con marcadores de capítulo; si una aplicación no muestra los capítulos, pruebe VLC, Apple Books o Audiobookshelf.

### 8. Ubicación de los datos y mantenimiento

- **Docker:** las voces, los proyectos y el audio se almacenan en el volumen `audiolibro-data` (los volúmenes se listan con `docker volume ls`; el nombre lleva como prefijo el de la carpeta). Copia de seguridad: `docker cp audiolibro-libre:/data ./copia-audiolibro`.
- **Sin Docker:** la carpeta `data/` junto al proyecto (o la indicada en `AUDIOLIBRO_DATA`).
- **Detener sin borrar nada:** `docker compose down`. **Borrar todo** (incluidas las voces y los proyectos): `docker compose down -v`.
- **Actualizar:** descargue la nueva versión, sustituya los archivos y ejecute `docker compose up -d --build` (los datos se conservan). Sin Docker, vuelva a ejecutar el instalador.

### 9. La aplicación se cerró durante la generación

No se pierde trabajo: cada fragmento se guarda al terminar. Abra la aplicación, vaya a «Mis proyectos», abra el proyecto y seleccione **Reanudar**. Solo se generan los fragmentos que faltan.

### 10. Notificación de un defecto

Abra una incidencia (*issue*) que incluya: sistema operativo, forma de ejecución (Docker, scripts o Colab), el **texto exacto** del cuadro de error rojo, la salida de `http://localhost:8000/api/system` y, si es posible, las últimas líneas del registro (sección 1). **No adjunte libros con copyright.**
