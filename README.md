# AudioLibro Libre

**ES:** Convierte un libro (`.epub`, `.pdf`, `.docx`, `.txt`, `.md`) en un audiolibro con capítulos. Gratis, en tu ordenador, sin cuentas, sin claves y sin enviar el libro a ningún servidor.
**EN:** Turn a book (`.epub`, `.pdf`, `.docx`, `.txt`, `.md`) into an audiobook with chapters. Free, on your own computer, no accounts, no API keys, nothing leaves your machine.

> ⚠️ **Aviso legal / Legal notice.** Debes tener los derechos del libro que conviertes. La herramienta no incluye ni distribuye libros con copyright. / You must have the rights to any book you convert. This tool does not include or distribute copyrighted books.

> 🚧 **Estado: fase 3.** Funciona: EPUB, PDF (con OCR opcional de escaneados), DOCX, TXT y MD; limpieza de cabeceras/pies/notas; voces Piper; diccionario de pronunciación; MP3 por capítulo con ID3/portada y M4B único con marcadores de capítulo; ZIP; estimaciones de tiempo/disco/RAM medidas en tu equipo. Pendiente (ver `docs/DECISIONS.md`): Kokoro, Docker, instaladores y guía visual completa.

## Probarlo ya (desarrollo)

Necesitas Python 3.10+, `ffmpeg` y `espeak-ng` instalados (Linux: `sudo apt install ffmpeg espeak-ng`). Para PDFs escaneados, opcionalmente Tesseract (`sudo apt install tesseract-ocr tesseract-ocr-spa`).

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
python -m app          # abre http://localhost:8000
```

En la primera pantalla pulsa **«Probar con Don Quijote»** (dominio público): en ~2 minutos tienes un audiolibro.

## Comprobar el código (sin CI, todo local)

```bash
./check.sh        # ruff + pytest
```

## Cómo funciona

Texto → capítulos → fragmentos → fonemas (espeak-ng) → modelo de voz (Piper, ONNX, CPU) → FLAC por fragmento en disco → MP3 con ffmpeg. Cada fragmento se guarda al terminar, así que se puede pausar, cancelar y reanudar sin perder nada.

Licencia: MIT. Dependencias y voces: [`LICENSES.md`](LICENSES.md). Decisiones técnicas: [`docs/DECISIONS.md`](docs/DECISIONS.md).
