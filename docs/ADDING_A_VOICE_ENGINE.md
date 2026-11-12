# Cómo añadir un motor de voz

El resto de la aplicación solo conoce la interfaz `TTSEngine` (`app/tts/base.py`). Añadir un motor **no requiere tocar** extractores, cola, exportación ni API: solo registrar una clase, su catálogo y una opción en la interfaz.

## 0. Antes de escribir código: verifica la licencia

El motor debe cumplir las reglas del proyecto (ver `CONTRIBUTING.md`): gratis, local, CPU, **licencia permisiva** (MIT/Apache-2.0/BSD…) tanto del **código** como de los **pesos del modelo y de cada voz**.

1. Lee la licencia en la **fuente oficial** (ficha del modelo en Hugging Face / PyPI), no en blogs.
2. Mira también las **dependencias** que arrastra (así se descartaron `kokoro-onnx` y `piper-tts`: dependían de GPL). Si un componente copyleft es imprescindible, solo puede ejecutarse como **programa externo independiente** (como espeak-ng) y debe quedar documentado.
3. Comprueba calidad en español e inglés, velocidad en CPU y RAM **ejecutándolo** (hay una guía en `docs/DECISIONS.md`: se usó reconocimiento de voz como proxy de inteligibilidad).
4. Anota los hallazgos en `docs/DECISIONS.md`.

## 1. Implementa la clase

```python
# app/tts/miotromotor.py
from app.tts.base import Audio, TTSEngine, VoiceInfo

class MiMotor(TTSEngine):
    id = "mimotor"        # identificador estable (se guarda en los proyectos)
    name = "Mi motor"

    def list_voices(self, lang=None) -> list[VoiceInfo]:
        """Voces del catálogo con `installed` informado. `size_bytes` = lo que falta por descargar AHORA."""

    def is_installed(self, voice_id: str) -> bool: ...

    def install(self, voice_id, progress=None, cancel=None) -> None:
        """Descarga con tools de app/tts/download.py (progreso, tamaño y SHA-256). Errores: UserError."""

    def synthesize(self, text, voice_id, *, speed=1.0, speaker=0) -> Audio:
        """Texto (una o varias frases) -> Audio(samples float32 mono en [-1, 1], sample_rate)."""

    def problems(self) -> list[str]:
        """Códigos de problemas del sistema (p. ej. ["espeak_missing"]); vacío si todo está bien."""
```

Reglas del contrato:
- `synthesize` es **determinista respecto a sus entradas** (la caché depende de ello) y no debe mantener estado entre llamadas salvo el modelo cargado. Debe ser seguro llamarlo desde un hilo.
- Devuelve audio **mono** `float32`. La frecuencia puede ser la que quieras: la exportación la remuestrea.
- Si el modelo funciona mal con frases cortas o muy largas, agrupa/divide dentro del motor (Kokoro agrupa hasta 400 tokens; Piper parte frases de > 260 caracteres).
- Usa `app.cleaning.sentences.split_sentences` / `split_long` y `app.tts.phonemize.phonemize` si necesitas frases o fonemas.
- Los errores para el usuario son `UserError("codigo", ...)`; **añade `errors.codigo.msg` y `.hint` a `es.json` y `en.json`** (una prueba lo exige).
- `VoiceInfo.lang` debe ser `"es"` o `"en"`; `license` una licencia permisiva; `attribution_required` si la licencia lo exige (se incluirá en `CREDITOS.txt`).

## 2. Regístralo

En `app/tts/__init__.py`:

```python
def _mimotor() -> TTSEngine:
    from app.tts.miotromotor import MiMotor
    return MiMotor()

_FACTORIES = {"piper": _piper, "kokoro": _kokoro, "mimotor": _mimotor}
```

## 3. Catálogo y créditos

- Genera el catálogo de voces con una herramienta en `tools/` que **verifique la licencia desde la fuente oficial y se niegue a continuar si no es permisiva** (modelos: `tools/audit_voices.py` para Piper y `tools/audit_kokoro.py` para Kokoro).
- Añade la sección del motor en `tools/gen_licenses.py` y regenera: `python tools/gen_licenses.py > LICENSES.md`.
- Añade la rama del motor en `app/export/metadata.py::voice_credit`.

## 4. Interfaz

- `app/web/static/index.html`: una `<option>` en `#engine`.
- `app/web/static/app.js`: la voz recomendada por idioma en `RECOMMENDED`.
- `i18n/es.json` y `en.json`: `s3.engine_<id>` con una descripción **honesta** (velocidad, tamaño de descarga, RAM).

## 5. Caché

Si cambias cómo se genera el audio de un motor ya existente, sube `CACHE_VERSION` en `app/jobs/chunking.py`. El identificador del motor ya forma parte de la clave de cada fragmento.

## 6. Pruebas (obligatorias)

- `tests/test_project_files.py::test_every_registered_engine_honours_the_contract` recorre todos los motores registrados y comprueba el contrato (voces en `es` y `en`, licencias, `voice_info`, `problems`).
- Prueba el motor **sin descargar** modelos grandes: sustituye la sesión ONNX por una simulada (ver `tests/test_kokoro.py`) y la descarga por una función falsa que escriba ficheros.
- Una prueba real opcional, protegida por `AUDIOLIBRO_TEST_DOWNLOADS=1` y marcada `slow`.
- **Ejecuta la aplicación y compara con el texto** (por ejemplo con un reconocedor de voz local) antes de decir que funciona bien.
- `./check.sh` debe pasar.

## Lista de comprobación

- [ ] Licencia de código, pesos y voces verificada en fuente oficial y documentada en `LICENSES.md`
- [ ] Ninguna dependencia GPL/AGPL/NC (o solo como programa externo documentado)
- [ ] Funciona en CPU y sin internet tras descargar los modelos
- [ ] Contrato `TTSEngine` y prueba de contrato en verde
- [ ] Textos en `es.json` y `en.json`; errores con `.hint`
- [ ] Hallazgos y mediciones en `docs/DECISIONS.md`
