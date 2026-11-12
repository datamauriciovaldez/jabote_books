"""Rutas y ajustes globales. Todo se guarda bajo una única carpeta de datos."""
from __future__ import annotations

import os
from pathlib import Path


def data_dir() -> Path:
    """Carpeta de datos (voces, proyectos, audio). Configurable con AUDIOLIBRO_DATA."""
    base = Path(os.environ.get("AUDIOLIBRO_DATA", "data")).expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)
    return base


def voices_dir() -> Path:
    d = data_dir() / "voices"
    d.mkdir(parents=True, exist_ok=True)
    return d


def jobs_dir() -> Path:
    d = data_dir() / "jobs"
    d.mkdir(parents=True, exist_ok=True)
    return d


HF_BASE = os.environ.get("AUDIOLIBRO_HF_BASE", "https://huggingface.co/rhasspy/piper-voices/resolve/main")
HF_KOKORO_BASE = os.environ.get("AUDIOLIBRO_HF_KOKORO_BASE",
                                "https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX/resolve/main")
