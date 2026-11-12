# AudioLibro Libre — imagen para uso local. Construcción: `docker compose up` (ver README).
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    AUDIOLIBRO_DATA=/data \
    AUDIOLIBRO_HOST=0.0.0.0 \
    AUDIOLIBRO_PORT=8000 \
    AUDIOLIBRO_NO_BROWSER=1

# ffmpeg (audio), espeak-ng (fonemas; GPL-3 como programa aparte) y Tesseract (OCR de PDFs escaneados).
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg espeak-ng tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app
RUN pip install -e .

# Usuario sin privilegios; /data guarda voces, proyectos y audio (se conserva en un volumen).
RUN useradd --create-home --uid 1000 audiolibro \
    && mkdir -p /data \
    && chown -R audiolibro:audiolibro /data
USER audiolibro
VOLUME /data
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/api/system', timeout=4)"

CMD ["python", "-m", "app"]
