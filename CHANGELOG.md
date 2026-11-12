# Historial de cambios / Changelog

## 0.1.0

Primera versión completa.

- Asistente de 5 pasos (español e inglés): subir, revisar, voz y ajustes, generar, exportar.
- Formatos de entrada: EPUB, PDF (con OCR opcional de Tesseract), DOCX, TXT y Markdown.
- Limpieza de números de página, cabeceras/pies repetidos, notas al pie y guiones de fin de línea; detección de capítulos.
- Voces: Piper (rápido, por defecto; inferencia propia) y Kokoro-82M (opcional, más natural y más lento).
- Diccionario de pronunciación, muestra de 10 s, estimaciones de tiempo/disco/RAM medidas en tu equipo.
- Generación reanudable (cada fragmento se guarda en disco): pausar, cancelar y reanudar sin perder nada.
- Exportación: MP3 por capítulo con ID3 y portada, M4B con marcadores de capítulo, volumen normalizado, ZIP con créditos.
- Instalación: Docker (`docker compose up`), `install.sh`, `install.bat` y notebook opcional de Colab.
