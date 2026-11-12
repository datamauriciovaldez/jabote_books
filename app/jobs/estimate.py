"""Estimaciones de tiempo, disco y RAM antes de empezar."""
from __future__ import annotations

import json
from typing import Any

from app.config import data_dir

CHARS_PER_SECOND = 14.5        # voz natural en español/inglés a velocidad 1.0
FLAC_RATIO = 0.55              # tamaño aproximado de FLAC frente a PCM de 16 bits
MP3_BYTES_PER_SECOND = 8000    # 64 kbps
DEFAULT_RTF = 3.0              # tiempo real × (conservador) si aún no se ha medido nada


def _bench_file():
    return data_dir() / "bench.json"


def record_rtf(audio_seconds: float, wall_seconds: float) -> None:
    """Guarda la velocidad medida (media móvil) para dar estimaciones realistas."""
    if wall_seconds <= 0.05 or audio_seconds <= 0.5:
        return
    rtf = audio_seconds / wall_seconds
    try:
        prev = json.loads(_bench_file().read_text()).get("rtf", rtf)
    except (OSError, ValueError):
        prev = rtf
    _bench_file().write_text(json.dumps({"rtf": round(0.8 * prev + 0.2 * rtf, 3)}))


def measured_rtf() -> float:
    try:
        return float(json.loads(_bench_file().read_text())["rtf"])
    except (OSError, ValueError, KeyError):
        return DEFAULT_RTF


def estimate(total_chars: int, longest_chapter_chars: int, *, speed: float, sample_rate: int = 22050,
             voice_size_bytes: int = 63_000_000) -> dict[str, Any]:
    secs = total_chars / (CHARS_PER_SECOND * max(0.25, speed))
    longest = longest_chapter_chars / (CHARS_PER_SECOND * max(0.25, speed))
    pcm = sample_rate * 2
    rtf = measured_rtf()
    return {
        "audio_seconds": round(secs),
        "generation_seconds": round(secs / rtf),
        "rtf": round(rtf, 1),
        "rtf_measured": _bench_file().exists(),
        "disk_bytes": int(secs * pcm * FLAC_RATIO + longest * pcm + 2 * secs * MP3_BYTES_PER_SECOND),
        "ram_bytes": int(voice_size_bytes * 3 + 400_000_000),
    }
