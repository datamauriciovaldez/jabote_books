# Architecture / Arquitectura

**[English](#english) · [Español](#español)**

---

<a name="english"></a>
## English

AudioLibro Libre is a **local** web application: a FastAPI server provides both the API and a static front end (plain HTML, CSS and JavaScript, with no build step). All state lives in a single data folder; there is no external database, Redis or Celery.

```
 Browser (five-step wizard, es/en i18n)
      |  HTTP/JSON (localhost)
      v
 app/web ---- FastAPI API + static files
      |
      +-- app/extractors -> Book{chapters}   epub, pdf (+ocr), docx, txt, md
      +-- app/cleaning   -> cleanup, chapters, sentences, pronunciation
      +-- app/jobs       -> fragments, in-process queue, progress, estimates, JSON store
      +-- app/tts        -> TTSEngine -> piper, kokoro   (ONNX + external espeak-ng)
      +-- app/export     -> WAV/FLAC -> ffmpeg -> MP3, M4B, ZIP
```

### Data flow

1. **Upload** (`POST /api/jobs`): the file is saved to a temporary directory and `extractors.extract()` returns a `Book` (`title, author, language, chapters[], cover`). A PDF may go through OCR (`extractors/ocr.py`, Tesseract and pypdfium2); progress is polled with a *token* at `/api/uploads/{token}`.
2. **Cleanup** (`cleaning/`): `normalize.py` (whitespace, page numbers, footnotes, hyphenation, paragraphs), `pages.py` (repeated headers and footers, and PDF paragraphs), `chapters.py` (detection through "Chapter..." headings, roman numerals, numbering and Markdown), `sentences.py` (sentence splitting that preserves abbreviations) and `pronunciation.py` (dictionary).
3. **Project** (`jobs/store.py`): `data/jobs/<id>/job.json` holds the book, editable chapters, settings and state, written atomically under a lock. The user edits chapters (step 2) and settings (step 3).
4. **Plan** (`jobs/runner.build_plan` and `jobs/chunking.py`): each included chapter is split into paragraphs, sentences and then **fragments** (at most 300 characters). Each fragment has a **key** = hash(cache version, engine, voice, speaker, speed, text).
5. **Generation** (`jobs/runner.JobRunner`): a single worker thread fed by a `queue.Queue`. For every fragment without a file it calls `engine.synthesize()` and writes `chunks/<chapter>/<n>-<key>.flac` atomically. **Resuming means starting again**: existing fragments are skipped. Pause and cancel stop after the fragment in progress. At startup, `recover()` marks anything left *running* after an abrupt shutdown as *paused*.
6. **Export** (`export/`): `render_chapter_wavs` assembles each chapter (fragments and pauses) as a stream, `normalize_chapter` applies ffmpeg `loudnorm` to FLAC (in parallel), `encode_mp3` runs in parallel and `export_m4b` concatenates, encodes AAC and writes `FFMETADATA1` chapter markers and the cover, and `make_zip` adds `CREDITOS.txt` with the voice license.

### Data folder (`AUDIOLIBRO_DATA`; default `./data`, `/data` in Docker)

```
voices/                 Piper models (<id>.onnx + .json) and kokoro/ (model.onnx + <voice>.bin)
jobs/<id>/job.json      book, settings and state
jobs/<id>/cover.jpg     cover image
jobs/<id>/chunks/<ch>/  FLAC fragments (the "cache": it invalidates itself when text or settings change)
jobs/<id>/export/       MP3, M4B and ZIP
bench.json              measured speed of each voice on this computer (used for estimates)
```

### Voice engines (`app/tts`)

`TTSEngine` (`base.py`) defines `list_voices`, `voice_info`, `is_installed`, `install`, `synthesize` and `problems`. Engines are registered in `tts/__init__.py`.
- **Piper** (`piper.py`): in-house inference with `onnxruntime`. The id sequence is `BOS, PAD, (phoneme, PAD)..., EOS`; punctuation is preserved for intonation.
- **Kokoro** (`kokoro.py`): `input_ids`, `style` (a voice row selected by token count) and `speed`; audio at 24 kHz.
- **Phonemes** (`phonemize.py`): espeak-ng as an **external process** (GPL-3, never linked). The clauses of a fragment are sent in a single call separated by blank lines, because espeak-ng merges consecutive lines.
- Voices are downloaded on demand with progress; size and SHA-256 are verified (`download.py`).

### Concurrency

- `uvicorn` server (threads for synchronous endpoints), **one** generation worker, one thread per voice installation and one thread per export. `store.update_job` uses an `RLock` for writes.
- Export: up to four `ffmpeg` processes at once (`WORKERS`).

### API summary

`GET /api/system` · `GET /api/voices` · `POST /api/voices/{id}/install` · `POST /api/voices/{id}/sample` · `POST /api/jobs` · `POST /api/jobs/demo` · `GET/PUT /api/jobs/{id}[/book|/settings]` · `GET /api/jobs/{id}/estimate` · `POST /api/jobs/{id}/start|pause|cancel` · `GET /api/jobs/{id}/progress` · `GET /api/jobs/{id}/chapters/{c}/preview` · `POST/GET /api/jobs/{id}/cover` · `POST/GET /api/jobs/{id}/export` · `GET /api/jobs/{id}/download/{file}` · `GET /licencias`. Interactive documentation is available at `/api/docs`.

**Errors:** every `UserError(code, detail, **params)` is returned as `{"error":{"code","detail","params"}}`; the interface displays `errors.<code>.msg` and `.hint` from `i18n/*.json`. A test requires every code to have a message and a suggested action in both languages.

### Estimates

`jobs/estimate.py`: duration = characters / (16 chars/s x speed); time = duration / measured real-time factor of the voice (`bench.json`, measured once in about two seconds and updated after each generation); disk = fragments + normalized chapters + temporary files + MP3 + M4B + ZIP; RAM = model size x 3 + 400 MB (measured: Piper 0.58 GB, Kokoro 1.1 GB).

### Tests (`tests/`, `./check.sh`)

Extractors (with EPUB, PDF and DOCX files generated on the fly), cleanup, fragmentation, queue and resumption (with `FakeEngine`), real export with ffmpeg and ffprobe, the complete API through `TestClient`, i18n, licenses, installation files and repository consistency. There is no CI: tests run locally.

---

<a name="español"></a>
## Español

AudioLibro Libre es una aplicación web **local**: un servidor FastAPI proporciona tanto la API como una interfaz estática (HTML, CSS y JavaScript sin paso de compilación). Todo el estado reside en una única carpeta de datos; no hay base de datos externa, ni Redis ni Celery.

```
 Navegador (asistente de cinco pasos, i18n es/en)
      |  HTTP/JSON (localhost)
      v
 app/web ---- API FastAPI + archivos estáticos
      |
      +-- app/extractors -> Book{capítulos}   epub, pdf (+ocr), docx, txt, md
      +-- app/cleaning   -> limpieza, capítulos, frases, pronunciación
      +-- app/jobs       -> fragmentos, cola en proceso, progreso, estimaciones, almacén JSON
      +-- app/tts        -> TTSEngine -> piper, kokoro   (ONNX + espeak-ng externo)
      +-- app/export     -> WAV/FLAC -> ffmpeg -> MP3, M4B, ZIP
```

### Flujo de datos

1. **Subida** (`POST /api/jobs`): el archivo se guarda en un directorio temporal y `extractors.extract()` devuelve un `Book` (`title, author, language, chapters[], cover`). Un PDF puede pasar por OCR (`extractors/ocr.py`, Tesseract y pypdfium2); el progreso se consulta con un *token* en `/api/uploads/{token}`.
2. **Limpieza** (`cleaning/`): `normalize.py` (espacios, números de página, notas, guiones, párrafos), `pages.py` (cabeceras y pies repetidos, y párrafos de PDF), `chapters.py` (detección mediante encabezados «Capítulo…», números romanos, numeración y Markdown), `sentences.py` (división en frases que respeta las abreviaturas) y `pronunciation.py` (diccionario).
3. **Proyecto** (`jobs/store.py`): `data/jobs/<id>/job.json` contiene el libro, los capítulos editables, los ajustes y el estado, escritos de forma atómica y con bloqueo. El usuario edita los capítulos (paso 2) y los ajustes (paso 3).
4. **Plan** (`jobs/runner.build_plan` y `jobs/chunking.py`): cada capítulo incluido se divide en párrafos, frases y, después, **fragmentos** (como máximo 300 caracteres). Cada fragmento tiene una **clave** = hash(versión de caché, motor, voz, locutor, velocidad, texto).
5. **Generación** (`jobs/runner.JobRunner`): un único hilo trabajador alimentado por una `queue.Queue`. Por cada fragmento sin fichero llama a `engine.synthesize()` y escribe `chunks/<capítulo>/<n>-<clave>.flac` de forma atómica. **Reanudar equivale a volver a empezar**: los fragmentos existentes se omiten. Pausar y cancelar se detienen tras el fragmento en curso. Al arrancar, `recover()` marca como *pausado* todo lo que quedó *en ejecución* tras un cierre brusco.
6. **Exportación** (`export/`): `render_chapter_wavs` monta cada capítulo (fragmentos y pausas) en flujo continuo, `normalize_chapter` aplica `loudnorm` de ffmpeg a FLAC (en paralelo), `encode_mp3` se ejecuta en paralelo y `export_m4b` concatena, codifica AAC y escribe los marcadores de capítulo `FFMETADATA1` y la portada, y `make_zip` añade `CREDITOS.txt` con la licencia de la voz.

### Carpeta de datos (`AUDIOLIBRO_DATA`; por defecto `./data`, `/data` en Docker)

```
voices/                 modelos de Piper (<id>.onnx + .json) y kokoro/ (model.onnx + <voz>.bin)
jobs/<id>/job.json      libro, ajustes y estado
jobs/<id>/cover.jpg     portada
jobs/<id>/chunks/<cap>/ fragmentos FLAC (la «caché»: se invalida sola si cambian el texto o los ajustes)
jobs/<id>/export/       MP3, M4B y ZIP
bench.json              velocidad medida de cada voz en este ordenador (para las estimaciones)
```

### Motores de voz (`app/tts`)

`TTSEngine` (`base.py`) define `list_voices`, `voice_info`, `is_installed`, `install`, `synthesize` y `problems`. Los motores se registran en `tts/__init__.py`.
- **Piper** (`piper.py`): inferencia propia con `onnxruntime`. La secuencia de identificadores es `BOS, PAD, (fonema, PAD)..., EOS`; la puntuación se conserva para la entonación.
- **Kokoro** (`kokoro.py`): `input_ids`, `style` (una fila de la voz seleccionada según el número de tokens) y `speed`; audio a 24 kHz.
- **Fonemas** (`phonemize.py`): espeak-ng como **proceso externo** (GPL-3, nunca enlazado). Las cláusulas de un fragmento se envían en una sola llamada separadas por líneas en blanco, porque espeak-ng fusiona las líneas consecutivas.
- Las voces se descargan bajo demanda con progreso; el tamaño y el SHA-256 se verifican (`download.py`).

### Concurrencia

- Servidor `uvicorn` (hilos para los endpoints síncronos), **un** trabajador de generación, un hilo por cada instalación de voz y un hilo por cada exportación. `store.update_job` usa un `RLock` para las escrituras.
- Exportación: hasta cuatro procesos `ffmpeg` simultáneos (`WORKERS`).

### Resumen de la API

`GET /api/system` · `GET /api/voices` · `POST /api/voices/{id}/install` · `POST /api/voices/{id}/sample` · `POST /api/jobs` · `POST /api/jobs/demo` · `GET/PUT /api/jobs/{id}[/book|/settings]` · `GET /api/jobs/{id}/estimate` · `POST /api/jobs/{id}/start|pause|cancel` · `GET /api/jobs/{id}/progress` · `GET /api/jobs/{id}/chapters/{c}/preview` · `POST/GET /api/jobs/{id}/cover` · `POST/GET /api/jobs/{id}/export` · `GET /api/jobs/{id}/download/{archivo}` · `GET /licencias`. La documentación interactiva está disponible en `/api/docs`.

**Errores:** toda `UserError(código, detalle, **params)` se devuelve como `{"error":{"code","detail","params"}}`; la interfaz muestra `errors.<código>.msg` y `.hint` de `i18n/*.json`. Una prueba exige que cada código tenga un mensaje y una acción sugerida en ambos idiomas.

### Estimaciones

`jobs/estimate.py`: duración = caracteres / (16 car/s x velocidad); tiempo = duración / factor de tiempo real medido de la voz (`bench.json`, que se mide una vez en unos dos segundos y se actualiza con cada generación); disco = fragmentos + capítulos normalizados + temporales + MP3 + M4B + ZIP; RAM = tamaño del modelo x 3 + 400 MB (medido: Piper 0,58 GB, Kokoro 1,1 GB).

### Pruebas (`tests/`, `./check.sh`)

Extractores (con archivos EPUB, PDF y DOCX generados sobre la marcha), limpieza, fragmentación, cola y reanudación (con `FakeEngine`), exportación real con ffmpeg y ffprobe, API completa mediante `TestClient`, i18n, licencias, archivos de instalación y coherencia del repositorio. No hay CI: las pruebas se ejecutan en local.
