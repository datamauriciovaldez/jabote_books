# Contributing

**[English](#english) · [Español](#español)**

---

<a name="english"></a>
## English

Thank you for contributing. The purpose of this project is to let users convert a book into an audiobook at no cost and without technical knowledge. Every change should preserve that goal.

### Project rules

These rules are mandatory.

1. **Free for everyone.** No paid APIs, no APIs that require a key, no credits that can run out, and no services that require a payment card or registration.
2. **No CI/CD.** Do not add GitHub Actions, workflows, bots or external services. Checks run locally (`./check.sh`) and releases are published manually (see `docs/RELEASING.md`). A test fails if a `.github/` directory appears.
3. **Everything runs locally**, and the user's book is never sent to a server. After installation and model download, the application must work offline.
4. **Permissive licenses only** (MIT, Apache-2.0, BSD or similar) that allow commercial use. Before adding a dependency, model or voice, verify its license at the official source (PyPI, the model card) and document it in `LICENSES.md`.
   - Not allowed: non-commercial licenses and strong copyleft as a Python dependency (AGPL/GPL, CC-BY-NC, CC-BY-SA for voices), models such as XTTS/Coqui CPML or F5-TTS, and unofficial services such as `edge-tts`.
   - Already rejected (see `docs/DECISIONS.md`): `ebooklib` (AGPL), `pymupdf` (AGPL), `mutagen` (GPL), `piper-tts` 1.3 and later (GPL), `kokoro-onnx` and `phonemizer` (GPL).
   - GPL programs such as espeak-ng and ffmpeg may only be **executed as separate processes**; they are never linked or vendored into the repository.
5. **CPU first.** A GPU is optional and only accelerates processing.
6. **The repository is MIT-licensed.**

### Development environment

```bash
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
# ffmpeg and espeak-ng are also required (optionally tesseract-ocr and tesseract-ocr-spa)
python -m app                                      # http://localhost:8000
```

### Before submitting a change

```bash
./check.sh          # complete ruff + pytest run (about one minute)
./check.sh fast     # skips tests marked "slow"
```

- Tests that download large models (326 MB) are disabled by default: `AUDIOLIBRO_TEST_DOWNLOADS=1 pytest -m slow`.
- **Add a test for every defect you fix.** Several real defects in this project were found only by running the application, so verify with real data and not only with synthetic inputs.
- **Run the application** when you change the interface or the audio pipeline. Unit tests neither listen to audio nor render the interface.
- If a change alters the generated audio (phonemes, ids, engine), increment `CACHE_VERSION` in `app/jobs/chunking.py`.

### Style

- Python 3.10 or later, with type annotations and concise docstrings that explain the reason for the code. `ruff` is configured in `pyproject.toml`.
- **Build-free front end:** plain HTML, CSS and JavaScript in `app/web/static/`. No frameworks and no `npm`.
- **All user-facing strings** belong in both `app/web/static/i18n/es.json` and `en.json`, with identical keys (a test enforces this). Every API error has `errors.<code>.msg` and `.hint` entries describing the suggested action.
- Accessibility: labels on all fields, keyboard operation, sufficient contrast and `aria-live` regions for progress.
- Error messages must be written in plain language and always include the suggested action.
- Documentation is bilingual, with the English text first and the Spanish text second.

### Commits and review

Keep commits small and descriptive, with passing tests in each one. Describe what changes and how it was verified.

### Related documents

[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · [`docs/ADDING_A_VOICE_ENGINE.md`](docs/ADDING_A_VOICE_ENGINE.md) · [`docs/RELEASING.md`](docs/RELEASING.md) · [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) · [`docs/DECISIONS.md`](docs/DECISIONS.md)

---

<a name="español"></a>
## Español

Gracias por contribuir. El propósito de este proyecto es que los usuarios puedan convertir un libro en un audiolibro sin coste y sin conocimientos técnicos. Cada cambio debe preservar ese objetivo.

### Reglas del proyecto

Estas reglas son obligatorias.

1. **Gratuito para todos.** Sin APIs de pago, sin APIs que requieran una clave, sin créditos que puedan agotarse y sin servicios que exijan tarjeta de pago o registro.
2. **Sin CI/CD.** No se añaden GitHub Actions, flujos de trabajo, bots ni servicios externos. Las comprobaciones se ejecutan en local (`./check.sh`) y las versiones se publican manualmente (véase `docs/RELEASING.md`). Una prueba falla si aparece un directorio `.github/`.
3. **Todo se ejecuta en local** y el libro del usuario nunca se envía a un servidor. Tras la instalación y la descarga de los modelos, la aplicación debe funcionar sin conexión.
4. **Solo licencias permisivas** (MIT, Apache-2.0, BSD o similares) que permitan el uso comercial. Antes de añadir una dependencia, un modelo o una voz, verifique su licencia en la fuente oficial (PyPI, ficha del modelo) y documéntela en `LICENSES.md`.
   - No se admiten: licencias no comerciales ni copyleft fuerte como dependencia de Python (AGPL/GPL, CC-BY-NC, CC-BY-SA para voces), modelos como XTTS/Coqui CPML o F5-TTS, ni servicios no oficiales como `edge-tts`.
   - Ya descartadas (véase `docs/DECISIONS.md`): `ebooklib` (AGPL), `pymupdf` (AGPL), `mutagen` (GPL), `piper-tts` 1.3 y posteriores (GPL), `kokoro-onnx` y `phonemizer` (GPL).
   - Los programas GPL como espeak-ng y ffmpeg solo pueden **ejecutarse como procesos independientes**; nunca se enlazan ni se incluyen en el repositorio.
5. **CPU primero.** Una GPU es opcional y solo acelera el procesamiento.
6. **El repositorio tiene licencia MIT.**

### Entorno de desarrollo

```bash
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
# También se necesitan ffmpeg y espeak-ng (opcionalmente tesseract-ocr y tesseract-ocr-spa)
python -m app                                      # http://localhost:8000
```

### Antes de enviar un cambio

```bash
./check.sh          # ejecución completa de ruff + pytest (aproximadamente un minuto)
./check.sh fast     # omite las pruebas marcadas como «slow»
```

- Las pruebas que descargan modelos grandes (326 MB) están desactivadas por defecto: `AUDIOLIBRO_TEST_DOWNLOADS=1 pytest -m slow`.
- **Añada una prueba por cada defecto que corrija.** Varios defectos reales de este proyecto solo se detectaron al ejecutar la aplicación, por lo que debe verificarse con datos reales y no únicamente con entradas sintéticas.
- **Ejecute la aplicación** cuando modifique la interfaz o el flujo de audio. Las pruebas unitarias no escuchan el audio ni renderizan la interfaz.
- Si un cambio altera el audio generado (fonemas, identificadores, motor), incremente `CACHE_VERSION` en `app/jobs/chunking.py`.

### Estilo

- Python 3.10 o posterior, con anotaciones de tipos y docstrings concisos que expliquen el motivo del código. `ruff` está configurado en `pyproject.toml`.
- **Interfaz sin paso de compilación:** HTML, CSS y JavaScript sin frameworks en `app/web/static/`. Sin frameworks y sin `npm`.
- **Todas las cadenas visibles para el usuario** pertenecen a `app/web/static/i18n/es.json` y a `en.json`, con las mismas claves (una prueba lo verifica). Cada error de la API tiene entradas `errors.<código>.msg` y `.hint` que describen la acción sugerida.
- Accesibilidad: etiquetas en todos los campos, uso con teclado, contraste suficiente y regiones `aria-live` para el progreso.
- Los mensajes de error deben redactarse en lenguaje claro e incluir siempre la acción sugerida.
- La documentación es bilingüe: primero el texto en inglés y después el texto en español.

### Commits y revisión

Mantenga los commits pequeños y descriptivos, con las pruebas pasando en cada uno. Describa qué cambia y cómo se verificó.

### Documentos relacionados

[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · [`docs/ADDING_A_VOICE_ENGINE.md`](docs/ADDING_A_VOICE_ENGINE.md) · [`docs/RELEASING.md`](docs/RELEASING.md) · [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) · [`docs/DECISIONS.md`](docs/DECISIONS.md)
