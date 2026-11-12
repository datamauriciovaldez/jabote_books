"""Estimaciones de tiempo, disco y RAM antes de empezar."""
from __future__ import annotations

import json
from typing import Any

from app.config import data_dir

# Caracteres de texto por segundo de audio a velocidad 1.0, medido con Piper (davefx) incluyendo las pausas:
# 495 653 caracteres -> 29 665 s (16,7). Se usa un valor algo menor porque las novelas reales tienen más diálogos
# y párrafos cortos (más pausas).
CHARS_PER_SECOND = 16.0
FLAC_RATIO = 0.55              # tamaño aproximado de FLAC frente a PCM de 16 bits
MP3_BYTES_PER_SECOND = 8000    # 64 kbps
DEFAULT_RTF = 4.0              # tiempo real × si aún no se ha medido nada (prudente, pero no exagerado)


def _bench_file():
    return data_dir() / "bench.json"


def _load() -> dict[str, float]:
    try:
        return dict(json.loads(_bench_file().read_text()).get("voices", {}))
    except (OSError, ValueError, AttributeError):
        return {}


def record_rtf(voice_id: str, audio_seconds: float, wall_seconds: float, *, min_wall: float = 0.05) -> None:
    """Guarda la velocidad medida de ESTA voz en ESTE ordenador (media móvil).

    Las mediciones demasiado cortas (< `min_wall` s) se ignoran por ser ruido; la medición de referencia usa
    un mínimo bajo para que un motor muy rápido quede igualmente registrado.
    """
    wall_seconds = max(wall_seconds, 1e-3) if min_wall <= 0 else wall_seconds
    if wall_seconds <= min_wall or audio_seconds <= 0.5:
        return
    rtf = audio_seconds / wall_seconds
    voices = _load()
    voices[voice_id] = round(0.8 * voices.get(voice_id, rtf) + 0.2 * rtf, 3)
    _bench_file().write_text(json.dumps({"voices": voices}))


def measured_rtf(voice_id: str) -> float | None:
    return _load().get(voice_id)


def estimate(total_chars: int, longest_chapter_chars: int, *, speed: float, voice_id: str = "",
             sample_rate: int = 22050, voice_size_bytes: int = 63_000_000) -> dict[str, Any]:
    secs = total_chars / (CHARS_PER_SECOND * max(0.25, speed))
    longest = longest_chapter_chars / (CHARS_PER_SECOND * max(0.25, speed))
    pcm = sample_rate * 2
    measured = measured_rtf(voice_id) if voice_id else None
    rtf = measured or DEFAULT_RTF
    return {
        "audio_seconds": round(secs),
        "generation_seconds": round(secs / rtf),
        "rtf": round(rtf, 1),
        "rtf_measured": measured is not None,
        # Pico durante la exportación: fragmentos FLAC + capítulos normalizados (FLAC) + hasta 4 WAV temporales
        # en paralelo + MP3 + M4B + ZIP (que repite MP3 y M4B). Los temporales se borran al terminar.
        "disk_bytes": int(2 * secs * pcm * FLAC_RATIO + 4 * longest * pcm + 4 * secs * MP3_BYTES_PER_SECOND),
        "ram_bytes": int(voice_size_bytes * 3 + 400_000_000),
    }
