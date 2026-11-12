# Adding a voice engine / Cómo añadir un motor de voz

**[English](#english) · [Español](#español)**

---

<a name="english"></a>
## English

The rest of the application depends only on the `TTSEngine` interface (`app/tts/base.py`). Adding an engine **does not require changes** to the extractors, the queue, the export pipeline or the API: it only requires registering a class, its catalog and an option in the interface.

### 0. Before writing code: verify the license

The engine must meet the project rules (see `CONTRIBUTING.md`): free of charge, local, CPU-capable and **permissively licensed** (MIT, Apache-2.0, BSD and similar), for the **code**, the **model weights** and **each voice**.

1. Read the license at the **official source** (the Hugging Face model card or PyPI), not in secondary sources.
2. Also review the **dependencies** it pulls in. This is how `kokoro-onnx` and `piper-tts` were rejected: they depended on GPL components. If a copyleft component is unavoidable, it may only be run as a **separate external program** (as espeak-ng is) and this must be documented.
3. Check quality in Spanish and English, CPU speed and RAM by **running it**. `docs/DECISIONS.md` describes the approach used: speech recognition as a proxy for intelligibility.
4. Record the findings in `docs/DECISIONS.md`.

### 1. Implement the class

```python
# app/tts/myengine.py
from app.tts.base import Audio, TTSEngine, VoiceInfo

class MyEngine(TTSEngine):
    id = "myengine"       # stable identifier (stored in projects)
    name = "My engine"

    def list_voices(self, lang=None) -> list[VoiceInfo]:
        """Catalog voices with `installed` populated. `size_bytes` = what must still be downloaded NOW."""

    def is_installed(self, voice_id: str) -> bool: ...

    def install(self, voice_id, progress=None, cancel=None) -> None:
        """Download using app/tts/download.py (progress, size and SHA-256). Errors: UserError."""

    def synthesize(self, text, voice_id, *, speed=1.0, speaker=0) -> Audio:
        """Text (one or more sentences) -> Audio(float32 mono samples in [-1, 1], sample_rate)."""

    def problems(self) -> list[str]:
        """System problem codes (for example ["espeak_missing"]); empty when everything is fine."""
```

Contract rules:
- `synthesize` is **deterministic with respect to its inputs** (the cache depends on this) and must not keep state between calls other than the loaded model. It must be safe to call from a thread.
- Return **mono** `float32` audio. Any sample rate is acceptable: the export pipeline resamples.
- If the model performs poorly on very short or very long sentences, group or split inside the engine (Kokoro groups up to 400 tokens; Piper splits sentences longer than 260 characters).
- Use `app.cleaning.sentences.split_sentences` and `split_long`, and `app.tts.phonemize.phonemize`, when sentences or phonemes are needed.
- User-facing errors are `UserError("code", ...)`; **add `errors.code.msg` and `.hint` to `es.json` and `en.json`** (a test enforces this).
- `VoiceInfo.lang` must be `"es"` or `"en"`; `license` must be a permissive license; set `attribution_required` if the license demands it (it is then written to `CREDITOS.txt`).

### 2. Register it

In `app/tts/__init__.py`:

```python
def _myengine() -> TTSEngine:
    from app.tts.myengine import MyEngine
    return MyEngine()

_FACTORIES = {"piper": _piper, "kokoro": _kokoro, "myengine": _myengine}
```

### 3. Catalog and credits

- Generate the voice catalog with a tool in `tools/` that **verifies the license from the official source and refuses to continue if it is not permissive** (examples: `tools/audit_voices.py` for Piper and `tools/audit_kokoro.py` for Kokoro).
- Add the engine's section to `tools/gen_licenses.py` and regenerate: `python tools/gen_licenses.py > LICENSES.md`.
- Add the engine's branch to `app/export/metadata.py::voice_credit`.

### 4. Interface

- `app/web/static/index.html`: an `<option>` in `#engine`.
- `app/web/static/app.js`: the recommended voice per language in `RECOMMENDED`.
- `i18n/es.json` and `en.json`: `s3.engine_<id>` with an **honest** description (speed, download size, RAM).

### 5. Cache

If you change how an existing engine generates audio, increment `CACHE_VERSION` in `app/jobs/chunking.py`. The engine identifier is already part of every fragment's key.

### 6. Tests (mandatory)

- `tests/test_project_files.py::test_every_registered_engine_honours_the_contract` iterates over every registered engine and checks the contract (voices in `es` and `en`, licenses, `voice_info`, `problems`).
- Test the engine **without downloading** large models: replace the ONNX session with a simulated one (see `tests/test_kokoro.py`) and the download with a fake function that writes files.
- Add an optional real test, protected by `AUDIOLIBRO_TEST_DOWNLOADS=1` and marked `slow`.
- **Run the application and compare the output with the text** (for example with a local speech recognizer) before concluding that it works well.
- `./check.sh` must pass.

### Checklist

- [ ] License of code, weights and voices verified at the official source and documented in `LICENSES.md`
- [ ] No GPL, AGPL or non-commercial dependency (or only as a documented external program)
- [ ] Works on CPU and offline after the models are downloaded
- [ ] `TTSEngine` contract and contract test passing
- [ ] Strings in `es.json` and `en.json`; errors with `.hint`
- [ ] Findings and measurements recorded in `docs/DECISIONS.md`

---

<a name="español"></a>
## Español

El resto de la aplicación depende únicamente de la interfaz `TTSEngine` (`app/tts/base.py`). Añadir un motor **no requiere modificar** los extractores, la cola, la exportación ni la API: solo hay que registrar una clase, su catálogo y una opción en la interfaz.

### 0. Antes de escribir código: verificar la licencia

El motor debe cumplir las reglas del proyecto (véase `CONTRIBUTING.md`): gratuito, local, apto para CPU y con **licencia permisiva** (MIT, Apache-2.0, BSD y similares), tanto para el **código** como para los **pesos del modelo** y **cada voz**.

1. Lea la licencia en la **fuente oficial** (la ficha del modelo en Hugging Face o PyPI), no en fuentes secundarias.
2. Revise también las **dependencias** que arrastra. Así se descartaron `kokoro-onnx` y `piper-tts`: dependían de componentes GPL. Si un componente copyleft es imprescindible, solo puede ejecutarse como **programa externo independiente** (como espeak-ng) y debe documentarse.
3. Compruebe la calidad en español e inglés, la velocidad en CPU y la RAM **ejecutándolo**. `docs/DECISIONS.md` describe el enfoque empleado: reconocimiento de voz como indicador de inteligibilidad.
4. Registre los hallazgos en `docs/DECISIONS.md`.

### 1. Implementar la clase

```python
# app/tts/myengine.py
from app.tts.base import Audio, TTSEngine, VoiceInfo

class MyEngine(TTSEngine):
    id = "myengine"       # identificador estable (se guarda en los proyectos)
    name = "Mi motor"

    def list_voices(self, lang=None) -> list[VoiceInfo]:
        """Voces del catálogo con `installed` informado. `size_bytes` = lo que falta por descargar AHORA."""

    def is_installed(self, voice_id: str) -> bool: ...

    def install(self, voice_id, progress=None, cancel=None) -> None:
        """Descarga con app/tts/download.py (progreso, tamaño y SHA-256). Errores: UserError."""

    def synthesize(self, text, voice_id, *, speed=1.0, speaker=0) -> Audio:
        """Texto (una o varias frases) -> Audio(muestras float32 mono en [-1, 1], sample_rate)."""

    def problems(self) -> list[str]:
        """Códigos de problemas del sistema (por ejemplo ["espeak_missing"]); vacío si todo está bien."""
```

Reglas del contrato:
- `synthesize` es **determinista respecto a sus entradas** (la caché depende de ello) y no debe mantener estado entre llamadas salvo el modelo cargado. Debe poder invocarse con seguridad desde un hilo.
- Devuelva audio **mono** `float32`. Cualquier frecuencia de muestreo es válida: la exportación remuestrea.
- Si el modelo rinde mal con frases muy cortas o muy largas, agrupe o divida dentro del motor (Kokoro agrupa hasta 400 tokens; Piper divide las frases de más de 260 caracteres).
- Utilice `app.cleaning.sentences.split_sentences` y `split_long`, y `app.tts.phonemize.phonemize`, cuando necesite frases o fonemas.
- Los errores dirigidos al usuario son `UserError("codigo", ...)`; **añada `errors.codigo.msg` y `.hint` a `es.json` y `en.json`** (una prueba lo exige).
- `VoiceInfo.lang` debe ser `"es"` o `"en"`; `license` debe ser una licencia permisiva; establezca `attribution_required` si la licencia lo exige (se incluirá entonces en `CREDITOS.txt`).

### 2. Registrarlo

En `app/tts/__init__.py`:

```python
def _myengine() -> TTSEngine:
    from app.tts.myengine import MyEngine
    return MyEngine()

_FACTORIES = {"piper": _piper, "kokoro": _kokoro, "myengine": _myengine}
```

### 3. Catálogo y créditos

- Genere el catálogo de voces con una herramienta en `tools/` que **verifique la licencia en la fuente oficial y se niegue a continuar si no es permisiva** (ejemplos: `tools/audit_voices.py` para Piper y `tools/audit_kokoro.py` para Kokoro).
- Añada la sección del motor a `tools/gen_licenses.py` y regenere: `python tools/gen_licenses.py > LICENSES.md`.
- Añada la rama del motor en `app/export/metadata.py::voice_credit`.

### 4. Interfaz

- `app/web/static/index.html`: una `<option>` en `#engine`.
- `app/web/static/app.js`: la voz recomendada por idioma en `RECOMMENDED`.
- `i18n/es.json` y `en.json`: `s3.engine_<id>` con una descripción **veraz** (velocidad, tamaño de descarga, RAM).

### 5. Caché

Si cambia la forma en que un motor existente genera el audio, incremente `CACHE_VERSION` en `app/jobs/chunking.py`. El identificador del motor ya forma parte de la clave de cada fragmento.

### 6. Pruebas (obligatorias)

- `tests/test_project_files.py::test_every_registered_engine_honours_the_contract` recorre todos los motores registrados y comprueba el contrato (voces en `es` y `en`, licencias, `voice_info`, `problems`).
- Pruebe el motor **sin descargar** modelos grandes: sustituya la sesión ONNX por una simulada (véase `tests/test_kokoro.py`) y la descarga por una función falsa que escriba archivos.
- Añada una prueba real opcional, protegida por `AUDIOLIBRO_TEST_DOWNLOADS=1` y marcada como `slow`.
- **Ejecute la aplicación y compare la salida con el texto** (por ejemplo, con un reconocedor de voz local) antes de concluir que funciona correctamente.
- `./check.sh` debe pasar.

### Lista de comprobación

- [ ] Licencia del código, los pesos y las voces verificada en la fuente oficial y documentada en `LICENSES.md`
- [ ] Ninguna dependencia GPL, AGPL o no comercial (o solo como programa externo documentado)
- [ ] Funciona en CPU y sin conexión tras descargar los modelos
- [ ] Contrato `TTSEngine` y prueba de contrato en verde
- [ ] Cadenas en `es.json` y `en.json`; errores con `.hint`
- [ ] Hallazgos y mediciones registrados en `docs/DECISIONS.md`
