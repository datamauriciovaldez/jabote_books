# Cómo contribuir / Contributing

¡Gracias por ayudar! Este proyecto existe para que una persona **no técnica** convierta un libro en audiolibro sin pagar nada. Cada cambio debe respetar eso.

## Reglas del proyecto (no negociables)

1. **Todo es gratis para todo el mundo.** Sin APIs de pago, sin APIs con clave, sin créditos que se agoten, sin servicios que pidan tarjeta o registro.
2. **Sin CI/CD.** No añadas GitHub Actions, workflows, bots ni servicios externos. Las comprobaciones se ejecutan en local (`./check.sh`) y las versiones se publican a mano (`docs/RELEASING.md`). Hay una prueba que falla si aparece `.github/`.
3. **Todo corre en local**, sin enviar el libro a ningún servidor. Tras instalar y descargar los modelos debe funcionar sin internet.
4. **Solo licencias permisivas** (MIT, Apache-2.0, BSD o similar) compatibles con uso comercial. Antes de añadir una dependencia, un modelo o una voz: **verifica su licencia en la fuente oficial** (PyPI, ficha del modelo) y documéntala en `LICENSES.md`.
   - Prohibido: licencias no comerciales o con copyleft fuerte (AGPL/GPL como dependencia de Python, CC-BY-NC, CC-BY-SA para voces…), modelos como XTTS/Coqui CPML o F5-TTS, y servicios no oficiales como `edge-tts`.
   - Ya descartadas (ver `docs/DECISIONS.md`): `ebooklib` (AGPL), `pymupdf` (AGPL), `mutagen` (GPL), `piper-tts` ≥ 1.3 (GPL), `kokoro-onnx`/`phonemizer` (GPL).
   - Programas externos GPL (espeak-ng, ffmpeg) solo se **ejecutan como procesos aparte**, nunca se enlazan ni se incluyen en el repo.
5. **Funciona en CPU.** La GPU es opcional y solo acelera.
6. **Licencia del repo: MIT.**

## Preparar el entorno

```bash
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
# También necesitas ffmpeg y espeak-ng (y opcionalmente tesseract-ocr tesseract-ocr-spa)
python -m app                                      # http://localhost:8000
```

## Antes de enviar un cambio

```bash
./check.sh          # ruff + pytest completos (≈ 1 min)
./check.sh fast     # sin pruebas marcadas "slow"
```

- Las pruebas que descargan modelos grandes (326 MB) están desactivadas por defecto: `AUDIOLIBRO_TEST_DOWNLOADS=1 pytest -m slow`.
- **Escribe una prueba** para cada fallo que arregles. Este repo ya encontró varios fallos reales solo al ejecutar la aplicación (ver `docs/DECISIONS.md`): prueba con datos reales, no solo sintéticos.
- **Ejecuta la aplicación de verdad** si tocas la interfaz o el audio. Las pruebas unitarias no oyen audio ni ven la pantalla.
- Cambios que alteran el audio generado (fonemas, ids, motor): sube `CACHE_VERSION` en `app/jobs/chunking.py`.

## Estilo

- Python 3.10+, tipado, con docstrings breves en español explicando el *porqué*. `ruff` está configurado en `pyproject.toml`.
- **Interfaz sin build**: HTML, CSS y JavaScript vanilla en `app/web/static/`. Nada de frameworks ni `npm`.
- **Todas las cadenas visibles** van en `app/web/static/i18n/es.json` **y** `en.json` (con las mismas claves; una prueba lo comprueba). Cada error de la API tiene `errors.<código>.msg` y `.hint` (qué puedes hacer).
- Accesibilidad: etiquetas en todos los campos, uso con teclado, contraste suficiente, `aria-live` para el progreso.
- Mensajes de error en lenguaje humano, siempre con la acción sugerida.

## Commits y revisión

Commits pequeños y descriptivos (en español o inglés), con las pruebas pasando en cada uno. Describe qué cambia y **cómo lo verificaste**.

## Documentos útiles

[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · [`docs/ADDING_A_VOICE_ENGINE.md`](docs/ADDING_A_VOICE_ENGINE.md) · [`docs/RELEASING.md`](docs/RELEASING.md) · [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) · [`docs/DECISIONS.md`](docs/DECISIONS.md)

---

## English summary

Hard rules: everything free for everyone (no paid/keyed APIs, no credits, no registration), **no CI/CD of any kind**, 100 % local processing (works offline after setup), **permissive licenses only** (verify every dependency and voice at its official source and record it in `LICENSES.md`; GPL/AGPL/NC/SA are out, external GPL programs may only be run as separate processes), CPU-first, MIT repo.
Workflow: `pip install -e ".[dev]"`, then `./check.sh` (ruff + pytest). Add a test for every fix, run the real app when touching the UI or audio, keep all UI strings in both `i18n/es.json` and `en.json`, bump `CACHE_VERSION` when audio output changes, and keep the front end build-free (vanilla JS).
