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
