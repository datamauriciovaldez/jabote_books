# Arquitectura

AudioLibro Libre es una aplicación web **local**: un servidor FastAPI sirve a la vez la API y una interfaz estática (HTML/CSS/JS vanilla, sin build). Todo el estado vive en una carpeta de datos; no hay base de datos externa, ni Redis, ni Celery.

```
 Navegador (asistente de 5 pasos, i18n es/en)
      │  HTTP/JSON (localhost)
      ▼
 app/web ── API FastAPI + archivos estáticos
      │
      ├── app/extractors ─► Book{capítulos}   epub · pdf (+ocr) · docx · txt · md
      ├── app/cleaning   ─► limpieza, capítulos, frases, pronunciación
      ├── app/jobs       ─► fragmentos · cola en proceso · progreso · estimaciones · almacén JSON
      ├── app/tts        ─► TTSEngine ─► piper · kokoro   (ONNX + espeak-ng externo)
      └── app/export     ─► WAV/FLAC ─► ffmpeg ─► MP3 · M4B · ZIP
```

## Flujo de datos

1. **Subida** (`POST /api/jobs`): se guarda en un directorio temporal y `extractors.extract()` devuelve un `Book` (`title, author, language, chapters[], cover`). El PDF puede pasar por OCR (`extractors/ocr.py`, Tesseract + pypdfium2); el progreso se consulta con un *token* en `/api/uploads/{token}`.
2. **Limpieza** (`cleaning/`): `normalize.py` (espacios, números de página, notas, guiones, párrafos), `pages.py` (cabeceras/pies repetidos y párrafos de PDF), `chapters.py` (detección por encabezados «Capítulo…», romanos, numeración, Markdown), `sentences.py` (frases sin romper abreviaturas), `pronunciation.py` (diccionario).
3. **Proyecto** (`jobs/store.py`): `data/jobs/<id>/job.json` con libro, capítulos editables, ajustes y estado; escritura atómica y candado. El usuario edita capítulos (paso 2) y ajustes (paso 3).
4. **Plan** (`jobs/runner.build_plan` → `jobs/chunking.py`): cada capítulo incluido se divide en párrafos → frases → **fragmentos** (≤ 300 caracteres). Cada fragmento tiene una **clave** = hash(versión de caché, motor, voz, locutor, velocidad, texto).
5. **Generación** (`jobs/runner.JobRunner`): un único hilo trabajador con una cola `queue.Queue`. Por cada fragmento sin fichero, llama a `engine.synthesize()` y lo guarda como `chunks/<capítulo>/<n>-<clave>.flac` con escritura atómica. **Reanudar = volver a empezar**: los fragmentos existentes se saltan. Pausar/cancelar paran tras el fragmento en curso. Al arrancar, `recover()` pasa a *pausado* lo que quedó *en ejecución* tras un cierre brusco.
6. **Exportación** (`export/`): `render_chapter_wavs` monta cada capítulo (fragmentos + pausas) en streaming → `normalize_chapter` (ffmpeg `loudnorm`, a FLAC, en paralelo) → `encode_mp3` (en paralelo) y `export_m4b` (concat + AAC + marcadores `FFMETADATA1` + portada) → `make_zip` (+ `CREDITOS.txt` con la licencia de la voz).

## Carpeta de datos (`AUDIOLIBRO_DATA`, por defecto `./data`; en Docker `/data`)

```
voices/                 modelos de Piper (<id>.onnx + .json) y kokoro/ (model.onnx + <voz>.bin)
jobs/<id>/job.json      libro, ajustes y estado
jobs/<id>/cover.jpg     portada
jobs/<id>/chunks/<cap>/ fragmentos FLAC (la "caché": se invalida sola si cambia texto o ajustes)
jobs/<id>/export/       MP3, M4B y ZIP
bench.json              velocidad medida de cada voz en este ordenador (para estimar)
```

## Motores de voz (`app/tts`)

`TTSEngine` (`base.py`) define: `list_voices`, `voice_info`, `is_installed`, `install`, `synthesize`, `problems`. Los registra `tts/__init__.py`.
- **Piper** (`piper.py`): inferencia propia con `onnxruntime`. Secuencia de ids `BOS, PAD, (fonema, PAD)…, EOS`; la puntuación se conserva para la entonación.
- **Kokoro** (`kokoro.py`): `input_ids` + `style` (fila de la voz según nº de tokens) + `speed`; audio a 24 kHz.
- **Fonemas** (`phonemize.py`): espeak-ng como **proceso externo** (GPL-3, nunca enlazado). Las cláusulas de un fragmento van en una sola llamada separadas por líneas en blanco porque espeak-ng fusiona líneas consecutivas.
- Las voces se descargan bajo demanda con progreso, tamaño y SHA-256 verificados (`download.py`).

## Concurrencia

- Servidor `uvicorn` (hilos para los endpoints síncronos), **un** trabajador de generación, un hilo por instalación de voz y un hilo por exportación. `store.update_job` usa un `RLock` para las escrituras.
- Exportación: hasta 4 procesos `ffmpeg` a la vez (`WORKERS`).

## API (resumen)

`GET /api/system` · `GET /api/voices` · `POST /api/voices/{id}/install` · `POST /api/voices/{id}/sample` · `POST /api/jobs` · `POST /api/jobs/demo` · `GET/PUT /api/jobs/{id}[/book|/settings]` · `GET /api/jobs/{id}/estimate` · `POST /api/jobs/{id}/start|pause|cancel` · `GET /api/jobs/{id}/progress` · `GET /api/jobs/{id}/chapters/{c}/preview` · `POST/GET /api/jobs/{id}/cover` · `POST/GET /api/jobs/{id}/export` · `GET /api/jobs/{id}/download/{archivo}` · `GET /licencias`. Documentación interactiva en `/api/docs`.

**Errores**: toda `UserError(código, detalle, **params)` sale como `{"error":{"code","detail","params"}}`; la interfaz muestra `errors.<código>.msg` y `.hint` de `i18n/*.json`. Una prueba exige que cada código tenga mensaje y acción sugerida en ambos idiomas.

## Estimaciones

`jobs/estimate.py`: duración = caracteres / (16 car/s × velocidad); tiempo = duración / velocidad real medida de la voz (`bench.json`, se mide una vez en ≈ 2 s y se actualiza con cada generación); disco = fragmentos + capítulos normalizados + temporales + MP3 + M4B + ZIP; RAM = tamaño del modelo × 3 + 400 MB (medido: Piper 0,58 GB, Kokoro 1,1 GB).

## Pruebas (`tests/`, `./check.sh`)

Extractores (con EPUB/PDF/DOCX generados al vuelo), limpieza, fragmentación, cola y reanudación (con `FakeEngine`), exportación real con ffmpeg/ffprobe, API completa con `TestClient`, i18n, licencias, archivos de instalación y coherencia del repo. No hay CI: se ejecutan en local.
