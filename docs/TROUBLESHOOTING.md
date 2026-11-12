# Solución de problemas

Si la aplicación te muestra un cuadro rojo «Algo no ha ido bien», lee el **«Qué puedes hacer»**: casi siempre resuelve el problema. Esta guía amplía los casos más comunes.

## 1. Cómo ver qué está pasando

| Cómo la ejecutas | Dónde mirar |
|---|---|
| Docker | `docker compose logs -f` (Ctrl+C para salir) o la pestaña *Logs* del contenedor en Docker Desktop |
| `install.bat` / `install.sh` | La propia ventana de la terminal |
| Fallo al instalar dependencias | `.venv/install.log` |
| Cualquiera | `http://localhost:8000/api/system` muestra si están ffmpeg, espeak-ng y Tesseract |

## 2. La aplicación no arranca / no se abre

**Docker**
- *«Cannot connect to the Docker daemon»* / *Docker no se inicia*: abre Docker Desktop y espera a que diga «Running». En Windows, Docker Desktop necesita **WSL 2** y la **virtualización activada en la BIOS**; si no puedes, usa `install.bat`.
- *Puerto 8000 ocupado* (`port is already allocated`): cambia en `docker-compose.yml` `"127.0.0.1:8000:8000"` por `"127.0.0.1:8080:8000"` y abre <http://localhost:8080>.
- *Quiero verla desde el móvil en mi casa*: por seguridad solo escucha en tu ordenador (`127.0.0.1`). Si de verdad lo necesitas, cambia a `"8000:8000"`, sabiendo que cualquiera de tu red podrá usarla.
- *Primera vez muy lenta*: construir la imagen descarga ~1 GB (Python, ffmpeg, Tesseract). Es una sola vez.

**Sin Docker**
- *«No he encontrado Python 3.10 o superior»*: instala Python desde <https://www.python.org/downloads/> (en Windows marca **«Add python.exe to PATH»**).
- *`No module named venv`* (Debian/Ubuntu): `sudo apt install python3-venv`.
- *Falló la instalación de dependencias*: casi siempre es la conexión. Mira `.venv/install.log` y vuelve a ejecutar el instalador.
- Windows: si `install.bat` se cierra al instante, ábrelo desde una ventana `cmd` para ver el mensaje.

## 3. Programas externos que faltan

| Programa | Para qué | Windows | Mac | Linux |
|---|---|---|---|---|
| **ffmpeg** | crear MP3/M4B | `winget install Gyan.FFmpeg` | `brew install ffmpeg` | `sudo apt install ffmpeg` |
| **espeak-ng** | pronunciación | instalador `.msi` de <https://github.com/espeak-ng/espeak-ng/releases> | `brew install espeak-ng` | `sudo apt install espeak-ng` |
| **Tesseract** (opcional) | OCR de PDF escaneados | <https://github.com/UB-Mannheim/tesseract/wiki> (marca *Spanish*) | `brew install tesseract tesseract-lang` | `sudo apt install tesseract-ocr tesseract-ocr-spa` |

Tras instalarlos, **cierra y reabre** la aplicación. Si espeak-ng está instalado pero la app no lo encuentra, indica su ruta con la variable de entorno `AUDIOLIBRO_ESPEAK` (p. ej. `C:\Program Files\eSpeak NG\espeak-ng.exe`). En Windows también se busca en las rutas habituales del instalador.

## 4. Voces

- **«No se ha podido conectar para descargar la voz»**: se necesita internet **solo** para este paso. Si estás tras un proxy o cortafuegos, permite `huggingface.co`.
- **«El archivo de la voz se descargó incompleto o dañado»**: pulsa «Descargar voz» otra vez (cada descarga se verifica con SHA-256).
- **Instalación manual** (sin acceso desde esta máquina): en otro ordenador descarga los dos archivos de la voz de Piper (`<id>.onnx` y `<id>.onnx.json`) desde `huggingface.co/rhasspy/piper-voices` y cópialos a `data/voices/`. Para Kokoro: `model.onnx` y `<voz>.bin` de `onnx-community/Kokoro-82M-v1.0-ONNX` en `data/voices/kokoro/`.
- **Una voz suena «robótica» o corta palabras**: prueba otra voz (las de calidad *media/alta* suenan mejor que *baja/básica*) o Kokoro (más natural, pero más lento).

## 5. El libro

- **EPUB con DRM**: no se puede leer. Usa una copia sin protección de un libro sobre el que tengas derechos.
- **PDF de varias columnas** o con mucho formato: el texto puede salir desordenado. Revísalo en el paso 2 o conviértelo antes a EPUB/TXT.
- **PDF escaneado**: se reconoce con OCR (necesita Tesseract). Un libro de 300 páginas tarda unos 5 minutos; no cierres la pestaña.
- **Capítulos mal detectados**: en el paso 2 puedes renombrar, añadir, quitar y desmarcar capítulos, y editar el texto. Si tu TXT no marca los capítulos, añade líneas como `Capítulo 1` separadas por una línea en blanco.
- **Caracteres raros en un TXT**: guárdalo con codificación UTF-8.
- **Se lee el índice o los agradecimientos**: desmarca esos capítulos en el paso 2.

## 6. Pronunciación

En el paso 3 abre el **diccionario de pronunciación** y escribe, en la columna derecha, cómo debe sonar (escrito como se pronuncia): `WiFi` → `guai fai`, `ONU` → `onu`, `Hermione` → `Jermaione`. Se aplica a todo el libro y solo regenera los fragmentos afectados. Para depurar, usa la **muestra de 10 s**.

## 7. Rendimiento, memoria y disco

- **Va lento**: usa **Piper** (≈ 25× más rápido que Kokoro), cierra otros programas y mira la estimación del paso 3 (se mide en tu equipo). Un portátil antiguo puede tardar 2–5× más que el de las mediciones del README.
- **Poca memoria**: Piper usa ≈ 0,6 GB y Kokoro ≈ 1,1 GB; los libros largos no aumentan la RAM (se procesan por fragmentos).
- **Disco lleno**: un libro de 8 h ocupa ≈ 1,6 GB (≈ 2,7 GB durante la exportación). Borra proyectos viejos en «Mis proyectos».
- **El M4B no se reproduce bien**: usa los MP3. El M4B es AAC mono de 64 kbps con marcadores de capítulo; si tu app no muestra los capítulos, prueba VLC, Apple Books o Audiobookshelf.

## 8. Tus datos

- **Docker**: voces, proyectos y audio están en el volumen `audiolibro-data` (se ve con `docker volume ls`; su nombre lleva como prefijo el de la carpeta). Copia de seguridad: `docker cp audiolibro-libre:/data ./copia-audiolibro`.
- **Sin Docker**: carpeta `data/` junto al proyecto (o la que indiques con `AUDIOLIBRO_DATA`).
- **Parar sin borrar nada**: `docker compose down`. **Borrar TODO** (incluidas las voces y los proyectos): `docker compose down -v`.
- **Actualizar**: descarga la versión nueva, sustituye los archivos y ejecuta `docker compose up -d --build` (los datos se conservan). Sin Docker, vuelve a ejecutar el instalador.

## 9. Se cerró a mitad de generación

No se pierde nada: cada fragmento se guarda al terminar. Abre la aplicación, entra en «Mis proyectos», abre el proyecto y pulsa **Reanudar**. Solo se generará lo que faltaba.

## 10. Reportar un fallo

Abre una *issue* con: sistema operativo, cómo la ejecutas (Docker / scripts / Colab), el **texto exacto** del cuadro rojo, la salida de `http://localhost:8000/api/system` y, si puedes, las últimas líneas del registro (sección 1). **No adjuntes tu libro** si tiene copyright.
