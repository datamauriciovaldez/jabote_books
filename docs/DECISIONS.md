# Decisiones técnicas y verificación de licencias

Investigación hecha el 2026-11-12 contra PyPI y Hugging Face (metadatos oficiales).
Regla del proyecto: gratis, local, CPU, licencias permisivas aptas para uso comercial. El repo es MIT.

## 1. Motor por defecto: Piper (modelos) con inferencia propia

**Hallazgo.** El paquete oficial `piper-tts` ≥ 1.3 (actual: 1.8.0, repo `OHF-Voice/piper1-gpl`) es **GPL-3.0-or-later**. La última versión MIT es `piper-tts` 1.2.0, que depende de `piper-phonemize` (ruedas con espeak-ng GPL empaquetado, solo para Python 3.10–3.11). Además, voces nuevas en español (`davefx`, `sharvard`) indican "Requires Piper 1.5 or higher".

**Decisión (aprobada por el usuario).** No dependemos del paquete `piper-tts`. Escribimos nuestra propia inferencia (MIT) en `app/tts/piper.py`:
texto → fonemas (espeak-ng externo) → ids según el `.onnx.json` de la voz → `onnxruntime` (MIT) → audio PCM.
Los modelos `.onnx` de Piper son datos, no código GPL.

**Riesgo asumido y mitigación.** Hay que implementar el formato de Piper 1.5+ (campos extra del JSON) y validarlo contra audio real en la Fase 1. Si alguna voz no cuadra, se marca como no soportada.

## 2. espeak-ng (GPL-3.0) — componente común a Piper y Kokoro

Ambos motores necesitan un fonemizador. espeak-ng es GPL-3.0. Decisión: **se invoca solo como programa externo por `subprocess`**, nunca se enlaza ni se incluye en el repo; Docker y los instaladores lo instalan en el sistema del usuario. El audio generado no queda afectado. Se documenta en `LICENSES.md` como "componente externo copyleft, aislado". Nota honesta: no es un componente permisivo; es la única excepción y es sustituible (la interfaz `TTSEngine` permite otro fonemizador en el futuro).

## 3. Kokoro-82M (opcional, Fase 4)

- Pesos `hexgrad/Kokoro-82M`: **Apache-2.0** ✅. ONNX `onnx-community/Kokoro-82M-v1.0-ONNX`: Apache-2.0 ✅.
- Voces en español: `ef_dora`, `em_alex`, `em_santa` (pocas, pero existen).
- `kokoro-onnx` (PyPI 0.6.1) arrastra `phonemizer` (**GPL-3**) y `espeakng-loader`. **No se usa el paquete**: cargaremos el modelo ONNX con nuestro código, reutilizando el mismo fonemizador externo del punto 2. Pendiente de verificar en Fase 4: formato de entrada de fonemas del ONNX y licencia exacta del archivo de voces `voices.bin`.

## 4. Voces de Piper: licencia por voz

`rhasspy/piper-voices` es MIT, pero **cada voz tiene su dataset y licencia**. El catálogo de la app tendrá una lista blanca: **CC0, dominio público, CC-BY, Apache-2.0, MIT**. Se excluyen CC-BY-SA, CC-BY-NC y desconocidas.

| Voz | Licencia del dataset | Estado |
|---|---|---|
| es_ES davefx (medium) | CC0 | ✅ candidata por defecto |
| es_ES carlfm (x_low) | Dominio público | ✅ (calidad baja) |
| es_MX claude (high) | Apache-2.0 | ✅ |
| es_ES mls_9972 (low) | CC BY 4.0 | ✅ con atribución |
| es_ES sharvard (medium) | CC BY 3.0 | ✅ con atribución |
| es_AR daniela (high) | CC BY-SA 4.0 | ❌ excluida |

Las voces en inglés se auditan igual en la Fase 1 leyendo cada `MODEL_CARD`. `LICENSES.md` se genera a partir de esas fichas.

## 5. Dependencias Python (verificadas)

| Necesidad | Elegida | Licencia | Descartada y por qué |
|---|---|---|---|
| Web | fastapi 0.162, uvicorn, pydantic, python-multipart, httpx | MIT / BSD / Apache | — |
| EPUB | `zipfile` + `lxml` + `beautifulsoup4` | stdlib / BSD / MIT | `ebooklib` = **AGPL-3.0** |
| PDF | `pypdf` (BSD) o `pdfminer.six` (MIT) | permisiva | `pymupdf` = **AGPL-3.0** |
| PDF→imagen (OCR) | `pypdfium2` | BSD / Apache | — |
| DOCX | `python-docx` | MIT | — |
| OCR | `pytesseract` + binario Tesseract (opcional) | Apache-2.0 | — |
| Inferencia | `onnxruntime`, `numpy`, `soundfile` | MIT / BSD | — |
| ID3 / M4B / portada | **ffmpeg por subprocess** | LGPL/GPL (programa externo) | `mutagen` = **GPL-2.0+** |
| Calidad | `pytest`, `ruff` | MIT | — |

ffmpeg se usa solo como ejecutable externo (no se redistribuye en el repo). En Docker se instala el paquete del sistema.

## 6. Otras decisiones

- **Python**: 3.10+ (probado aquí con 3.13). `onnxruntime` actual exige 3.11+; se fijará un rango compatible en `requirements.txt` y el instalador comprobará la versión.
- **Estado**: SQLite (stdlib) para trabajos; fragmentos de audio en disco (`work/<job>/chunks/<hash>.wav`), clave = hash(texto + voz + ajustes + pronunciación). Reanudar = saltar los existentes.
- **Cola**: un hilo trabajador en proceso con `threading` y eventos de pausa/cancelación; progreso por SSE.
- **Frontend**: vanilla, sin build, i18n en `web/static/i18n/{es,en}.json`.
- **Sin CI**: no habrá `.github/`. Tests y lint se ejecutan con `make check` / `./check.sh`.
- **Colab**: opcional; límites a documentar con honestidad (sesiones temporales, necesita internet, el libro sube a servidores de Google, lo que contradice "todo local": se avisará claramente).
- **Descargas**: solo los modelos desde Hugging Face, con barra de progreso y verificación de tamaño/hash.

## 7. Pendiente de verificar durante la implementación

1. Formato exacto del `.onnx.json` de Piper 1.5+ y calidad real en CPU (se mide en Fase 1).
2. Licencias de las voces en inglés.
3. Entradas del ONNX de Kokoro sin `phonemizer`.
4. Rendimiento: un EPUB de 300 páginas (~90 000 palabras ≈ 10 h de audio) en CPU; se medirá el factor de tiempo real.

## 8. Hallazgos de la Fase 1 (verificados ejecutando la app)

Verificación del audio: no se puede "escuchar" en el entorno de desarrollo, así que se transcribió el audio
generado con Whisper (solo como herramienta de desarrollo, no se distribuye) y se comparó con el texto.

1. **Secuencia de ids de Piper**: debe ser `BOS, PAD, (fonema, PAD)…, EOS`. Sin el PAD inicial se perdía el
   arranque de cada frase (error medio 26 % → 11 % con el PAD). Cubierto por `test_phoneme_ids_layout_matches_piper`.
2. **espeak-ng fusiona líneas consecutivas** en una sola frase: las cláusulas se separan con línea en blanco y,
   si el recuento no cuadra, se consulta cláusula a cláusula. Sin esto la puntuación se amontonaba al final y las
   comas perdían su pausa. Cubierto por `test_punctuation_stays_in_place`.
3. **EPUB sin declaración de codificación**: `lxml` asumía latin-1 ("tÃ­tulo"); ahora se decodifica explícitamente (UTF-8 por defecto).
4. `CACHE_VERSION` (en `app/jobs/chunking.py`) se sube cuando cambia algo que altera el audio, para no reutilizar fragmentos antiguos.
5. Resultados medidos (CPU de 4 núcleos): ~6–7× tiempo real con la voz `davefx`; volumen final −19,4 LUFS (objetivo −19);
   pausa/reanudación con Piper real: los fragmentos ya generados no se regeneran.
6. Voces: el catálogo auditado tiene 19 voces permisivas (7 es, 12 en). `lessac` (licencia Blizzard), las CC-BY-SA/NC y las
   de licencia "See URL" se descartan por prudencia.

## 9. Hallazgos de la Fase 2 (verificados con un PDF real generado con Chromium)

- **Guiones de PDF**: los PDF parten palabras con U+2010 (`‐`), no `-`. `fix_hyphenation` los cubre (regresión incluida).
- **Cabeceras repetidas**: se detectan comparando las 3 primeras y últimas líneas de cada página (≥ 40 % de páginas).
  Los dígitos solo se ignoran si están en un extremo de la línea ("12 Título"); los encabezados de capítulo
  ("Capítulo 1/2/3") nunca se normalizan, o se borraban como si fueran cabecera (bug real encontrado y corregido).
- **Notas al pie en PDF**: se descartan por tamaño de fuente (< 85 % de la dominante en el cuarto inferior de la página)
  usando el `visitor_text` de pypdf. No detecta notas con el mismo tamaño que el cuerpo.
- **OCR**: Tesseract (Apache-2.0) vía `pytesseract` + `pypdfium2` para renderizar a 250 dpi. Medido: ~1 s/página en CPU
  (≈ 5 min para 300 páginas) y 100 % de similitud de palabras sobre un escaneo limpio a 200 dpi. Se activa solo si
  ≥ 50 % de las páginas no tienen texto; si falta Tesseract o el idioma, la app lo explica con pasos de instalación.
- **Limitaciones conocidas**: no se tratan PDFs de varias columnas; un subtítulo bajo el título del capítulo puede fundirse
  con el primer párrafo (se corrige a mano en el paso 2); el OCR de escaneos muy sucios puede tener errores.
- **Dependencias nuevas** (todas permisivas): pypdf (BSD-3), python-docx (MIT), pypdfium2 (BSD-3/Apache-2.0),
  pytesseract (Apache-2.0), Pillow (MIT-CMU). Ver `LICENSES.md`.

## 10. Hallazgos de la Fase 3 (prueba larga con la app real)

Prueba: EPUB sintético de 81 174 palabras / 495 653 caracteres / 30 capítulos (≈ 290 páginas; `tools/make_test_epub.py`;
**no es una novela real**: mide rendimiento y estructura, no calidad literaria; Project Gutenberg está bloqueado por la red
del entorno de desarrollo). CPU de 4 núcleos, voz `es_ES-davefx-medium`, proxy bloqueado (sin internet), `kill -9` al 25 %.

| Medida | Resultado |
|---|---|
| Fragmentos / audio | 2 404 / 8,24 h (29 665 s) |
| Generación (incluye el `kill -9`) | 1 205 s (≈ 20 min, ≈ 25× tiempo real) |
| Reanudación tras `kill -9` | estado `paused 600/2404` al reiniciar; 0 fragmentos regenerados |
| RAM pico del servidor | 582 MB |
| Exportación M4B + 30 MP3 + ZIP | 1 611 s con el primer diseño → **791 s** tras paralelizar la normalización |
| Tamaños | M4B 245 MB; ZIP 483 MB; fragmentos FLAC 744 MB; total del proyecto 1,6 GB |
| M4B | 30 marcadores contiguos (hueco 0,0 s), 8,24 h, AAC 66 kbps, decodifica entero sin errores, salto a mitad de capítulo correcto, −19,1 LUFS |

Problemas encontrados y corregidos:
1. **Saturación**: con un `loudnorm` único sobre todo el libro y TP=-1,5 el M4B medía **+1,1 dBFS**. Ahora cada capítulo se normaliza una vez
   (TP=-2,5, a FLAC) y de ese FLAC salen MP3 y M4B: pico final −0,3 dBFS. Prueba de regresión `test_exports_do_not_clip_and_are_levelled`.
2. **Exportación lenta**: `loudnorm`+codificación en un solo hilo. Ahora normalización y MP3 van en paralelo (hasta 4 ffmpeg). El M4B final
   (AAC nativo, un solo hilo, ≈ 9 min para 8 h) sigue siendo secuencial.
3. **Estimación inicial ~10× pesimista** (decía 3,1 h; real 20 min): ahora se mide la velocidad de la voz en este ordenador (una vez,
   ≈ 2 s) y se guarda por voz. Con la medición: audio 30 763 s frente a 29 665 reales (+3,7 %), generación 1 379 s frente a 1 205 s (+14 %, conservadora),
   RAM 590 MB frente a 582 MB.
4. El M4B usa AAC-LC nativo de ffmpeg (sin libfdk, que no es libre), mono, 44,1 kHz, 64 kbps, `+faststart`, portada como `attached_pic`.

Límites: el pico final queda a solo 0,3 dB de 0 dBFS (sin saturar, pero con poco margen); el disco pico estimado (≈ 2,7 GB para 8 h) cuenta los temporales,
que se borran al terminar. No se ha probado en Apple Books/otros reproductores reales, solo con ffprobe/ffmpeg.

## 11. Fase 4: Kokoro-82M (verificado; se incluye como motor opcional)

**Licencia (fuente oficial, API de Hugging Face):** `hexgrad/Kokoro-82M` y `onnx-community/Kokoro-82M-v1.0-ONNX` declaran `apache-2.0`.
El README declara entrenamiento "exclusivamente con audio permisivo/no protegido por copyright" (algo de CC BY, p. ej. SIWIS y Koniwa; ver `LICENSES.md`).

**Implementación sin GPL:** `kokoro-onnx` depende de `phonemizer` (GPL-3), así que no se usa. Se reimplementa la inferencia (`app/tts/kokoro.py`):
fonemas IPA con nuestro espeak-ng externo → ids del vocabulario oficial (`config.json`, 114 símbolos, ids 1–177; el 0 es relleno) →
`model.onnx` con `input_ids` (relleno 0 al inicio y al final), `style` (fila `n_tokens-1` de la matriz 510×256 de la voz) y `speed` → audio a 24 kHz.
Las frases se agrupan hasta 400 tokens (Kokoro rinde mal con frases cortas; límite del modelo: 510).

**Medido (CPU de 4 núcleos), mismo capítulo de Cervantes y reconocimiento de voz como proxy de inteligibilidad:**

| | Piper (davefx) | Kokoro (ef_dora) |
|---|---|---|
| Diferencia con el texto (Whisper base) | 18 % | **12 %** (10 % con em_alex, ya en MP3) |
| Velocidad | ≈ 25× tiempo real | ≈ 3,5× tiempo real |
| Descarga | 63 MB por voz | 326 MB (modelo común) + 0,5 MB por voz |
| RAM pico | 582 MB | 1 095 MB |
| Voces en español | 7 | 3 (ef_dora, em_alex, em_santa) |

- **Un libro de ≈ 8 h de audio tardaría ≈ 2,4 h con Kokoro** frente a ≈ 20 min con Piper. Por eso Piper sigue siendo el motor por defecto y la interfaz lo explica.
- **Inglés:** Kokoro usa `misaki` como generador de pronunciación principal (no disponible sin dependencias extra); con espeak-ng directo
  (en-us / en-gb) las frases de prueba dieron 0 % de diferencia con af_heart y bf_emma. Es una aproximación: para algunas palabras `misaki` podría sonar mejor.
- **Variante int8 (`model_quantized.onnx`, 92 MB) descartada:** en este CPU fue **más lenta** (0,8× tiempo real) que fp32 (≈ 4×). Se usa fp32.
- **Catálogo:** 31 voces es/en generadas por `tools/audit_kokoro.py`, que verifica la licencia y el SHA-256 de cada archivo; se descargan con verificación.
- Los tests no descargan el modelo (sesión ONNX simulada); la prueba real se activa con `AUDIOLIBRO_TEST_DOWNLOADS=1`.

## 12. Fase 5: instalación y documentación

**Probado de verdad (Linux):**
- `install.sh --check` en una copia **limpia** con Python 3.11 (23 s) y arranque real con `install.sh`; suite completa (ruff + pytest) con Python 3.11.
- Camino de error con ffmpeg/espeak-ng ausentes del PATH: mensaje claro y código de salida 1.
- Pasos del `Dockerfile` **simulados** en un entorno limpio con Python 3.12 (`pip install -e .`, variables de entorno de la imagen, mismo *healthcheck*): HTTP 200.
- `docker compose config` valida el `docker-compose.yml`.
- Capturas del README tomadas de la aplicación real (incluido un error y la vista de móvil de 390 px, sin desbordes).

**Hallazgos:**
- `pip install -e .` imprime un aviso largo de `setuptools` que asustaría a una persona no técnica: los instaladores lo mandan a `.venv/install.log` y solo lo muestran si falla.
- `onnxruntime` actual exige Python ≥ 3.11 pero `pyproject.toml` declara ≥ 3.10: `pip` elige una versión compatible en 3.10, que **no se ha podido probar** (no hay Python 3.10 en el entorno).
- Docker con *volumen nombrado* (no *bind mount*) evita los problemas de permisos de `./data` en Linux; el puerto se publica solo en `127.0.0.1`.
- Docker Desktop no es gratuito para grandes empresas: el README lo avisa y ofrece la opción B (100 % libre).

**No se pudo probar (declarado en el README):** construir la imagen (hay cliente pero no motor de Docker ni acceso a registros), `install.bat` en Windows, `install.sh` en macOS, el notebook de Colab y la compatibilidad con Python 3.10. Una persona no técnica no ha seguido el README de principio a fin: se revisó punto por punto contra el comportamiento real, pero la prueba con un usuario real sigue pendiente.

## 13. App de escritorio para macOS (Apple Silicon): lo hecho y lo pendiente

**Decisión del usuario:** `.app` sin firmar para Apple Silicon (el amigo usa Mac). Firmar y notarizar (99 $/año) se descarta por la regla "todo gratis".

**Diseño:** lanzador `app/desktop.py` (ventana con pywebview, plan B navegador, `--self-test`), receta `packaging/audiolibro.spec` (PyInstaller) y scripts `tools/mac/*` que compilan **LAME + ffmpeg LGPL** (`--disable-gpl --disable-nonfree`) y **espeak-ng** estáticos, construyen la `.app`, la firman *ad hoc* (Apple Silicon exige alguna firma) y crean el `.dmg`.

**Cambio de criterio de licencias, solo para este instalador:** hasta ahora no se redistribuía ningún programa GPL (se pedía instalarlos al usuario). El `.dmg` los incluye, así que: ffmpeg se compila sin GPL; ffmpeg/LAME/espeak-ng se ejecutan como procesos independientes (sin enlazar); las licencias van dentro de la app; y **el código fuente exacto se publica junto al `.dmg`** (`dist/mac/sources/`). PyInstaller (GPL-2 + excepción del *bootloader*) es solo herramienta de construcción. pywebview BSD-3, PyObjC MIT (verificado en PyPI). Detalle en `packaging/THIRD_PARTY_NOTICES.md` y `LICENSES.md`.

**Verificado (en Linux):**
- Binario empaquetado con la misma receta (227 MB): autoprueba en verde y flujo completo sin el código fuente: generar con Piper (16/16), exportar M4B + 2 MP3, `/licencias`, catálogo de Kokoro (los imports perezosos y las bibliotecas nativas de onnxruntime/soundfile/pdfium se incluyeron bien).
- Lógica de descarga con verificación SHA-256 de `tools/mac/lib.sh` (hash correcto, incorrecto, sin fijar) con tarballs locales; sintaxis de los scripts; opciones de `configure` de LAME compiladas de verdad; la fuente de LAME 3.100 fijada y verificada (`ddfe36ca…da1e`).
- Dos fallos propios hallados al ejecutar el binario: la autoprueba calculaba rutas desde el script de entrada (en PyInstaller `__file__` apunta a otra carpeta) y la salida del servidor no se vaciaba al redirigirse a un archivo (`flush=True`).

**No verificado (requiere un Mac real; ver `docs/MAC_APP.md`):** compilar ffmpeg/espeak-ng allí (las fuentes de ffmpeg 7.1.1 y espeak-ng 1.52.0 **no tienen hash fijado**: ffmpeg.org y GitHub no son accesibles desde el entorno de desarrollo; el script muestra el hash calculado y exige `AUDIOLIBRO_TRUST_NEW_SOURCES=1` la primera vez), que exista la etiqueta `1.52.0`, `ESPEAK_DATA_PATH`, la ventana de pywebview (descargas y subida de archivos), la firma *ad hoc*, el `.dmg`, el comportamiento de cierre en el Dock y el macOS mínimo.

**Fuera de esta versión:** OCR (Tesseract) dentro de la app; PDF escaneados mostrarían "OCR no disponible".
