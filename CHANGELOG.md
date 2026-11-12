# Changelog / Historial de cambios

## Unreleased / Sin publicar

**English**
- Desktop launcher (`python -m app.desktop`) with a native window (pywebview), a browser mode and a self-test (`--self-test`).
- PyInstaller recipe and scripts to build **AudioLibro Libre.app** for macOS (Apple Silicon) with an LGPL ffmpeg and espeak-ng bundled; see `docs/MAC_APP.md`. Not yet verified on macOS.
- Build recipes rehearsed on Linux from pinned, verified sources (`tools/mac/rehearse_linux.sh`).
- Documentation restructured: English first, followed by Spanish.

**Español**
- Lanzador de escritorio (`python -m app.desktop`) con ventana nativa (pywebview), modo navegador y autoprueba (`--self-test`).
- Receta de PyInstaller y scripts para construir **AudioLibro Libre.app** para macOS (Apple Silicon) con un ffmpeg LGPL y espeak-ng incluidos; véase `docs/MAC_APP.md`. Aún sin verificar en macOS.
- Recetas de compilación ensayadas en Linux a partir de fuentes fijadas y verificadas (`tools/mac/rehearse_linux.sh`).
- Documentación reestructurada: primero en inglés y después en español.

## 0.1.0

First complete version. / Primera versión completa.

**English**
- Five-step wizard (English and Spanish): upload, review, voice and settings, generate, export.
- Input formats: EPUB, PDF (with optional Tesseract OCR), DOCX, TXT and Markdown.
- Removal of page numbers, repeated headers and footers, footnotes and end-of-line hyphenation; chapter detection.
- Voices: Piper (fast, default; in-house inference) and Kokoro-82M (optional, more natural and slower).
- Pronunciation dictionary, 10-second preview, and time, disk and RAM estimates measured on the user's machine.
- Resumable generation (each fragment is saved to disk): pause, cancel and resume without losing progress.
- Export: one MP3 per chapter with ID3 tags and cover art, M4B with chapter markers, normalized loudness and a ZIP with credits.
- Installation: Docker (`docker compose up`), `install.sh`, `install.bat` and an optional Colab notebook.

**Español**
- Asistente de cinco pasos (español e inglés): subir, revisar, voz y ajustes, generar, exportar.
- Formatos de entrada: EPUB, PDF (con OCR opcional de Tesseract), DOCX, TXT y Markdown.
- Eliminación de números de página, cabeceras y pies repetidos, notas al pie y guiones de fin de línea; detección de capítulos.
- Voces: Piper (rápido, por defecto; inferencia propia) y Kokoro-82M (opcional, más natural y más lento).
- Diccionario de pronunciación, muestra de 10 s y estimaciones de tiempo, disco y RAM medidas en el equipo del usuario.
- Generación reanudable (cada fragmento se guarda en disco): pausar, cancelar y reanudar sin perder el progreso.
- Exportación: un MP3 por capítulo con etiquetas ID3 y portada, M4B con marcadores de capítulo, volumen normalizado y un ZIP con créditos.
- Instalación: Docker (`docker compose up`), `install.sh`, `install.bat` y un cuaderno opcional de Colab.
