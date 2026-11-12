"""Lectura/escritura de fragmentos de audio y montaje de capítulos (en streaming, sin cargar todo en RAM)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import BinaryIO

import numpy as np
import soundfile as sf

from app.jobs.chunking import Chunk


def save_chunk(path: Path, samples: np.ndarray, sample_rate: int) -> None:
    """Escritura atómica: si se cancela a mitad, nunca queda un fichero corrupto."""
    tmp = path.with_name(path.stem + ".tmp.flac")
    sf.write(tmp, samples, sample_rate, format="FLAC", subtype="PCM_16")
    os.replace(tmp, path)


def assemble(chunks: list[Chunk], chunk_dir: Path, out: Path | BinaryIO, *, pause_paragraph: float,
             pause_chapter: float = 0.0, max_seconds: float | None = None, fmt: str = "WAV") -> float:
    """Une los fragmentos existentes de un capítulo. Devuelve los segundos escritos.

    Con `max_seconds` corta al llegar (vista previa). Se detiene en el primer fragmento que falte.
    """
    written = 0
    sr: int | None = None
    sink: sf.SoundFile | None = None
    try:
        for ch in chunks:
            f = chunk_dir / ch.filename
            if not f.exists():
                break
            data, rate = sf.read(f, dtype="float32")
            if sink is None:
                sr = rate
                sink = sf.SoundFile(out, "w", samplerate=rate, channels=1, format=fmt, subtype="PCM_16")
            sink.write(data)
            written += len(data)
            if ch.para_end and pause_paragraph > 0:
                pad = int(pause_paragraph * rate)
                sink.write(np.zeros(pad, dtype=np.float32))
                written += pad
            if max_seconds and written / rate >= max_seconds:
                break
        else:
            if sink is not None and sr and pause_chapter > 0:
                sink.write(np.zeros(int(pause_chapter * sr), dtype=np.float32))
                written += int(pause_chapter * sr)
    finally:
        if sink is not None:
            sink.close()
    return written / sr if sr else 0.0
