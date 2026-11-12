"""Audiolibro M4B: un único archivo AAC con marcadores de capítulo, portada y metadatos (ffmpeg)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import soundfile as sf

from app.export.mp3 import LOUDNORM, cover_path, run_ffmpeg, safe_name


@dataclass(frozen=True)
class ChapterAudio:
    """Un capítulo ya montado en WAV (con sus pausas)."""

    title: str
    wav: Path
    frames: int
    sample_rate: int

    @property
    def seconds(self) -> float:
        return self.frames / self.sample_rate


def measure(title: str, wav: Path) -> ChapterAudio:
    info = sf.info(str(wav))
    return ChapterAudio(title, wav, info.frames, info.samplerate)


def _esc(value: str) -> str:
    """Escapado de FFMETADATA1: = ; # \\ y saltos de línea."""
    for ch in ("\\", "=", ";", "#", "\n"):
        value = value.replace(ch, "\\" + ch)
    return value


def chapter_marks(chapters: list[ChapterAudio]) -> list[tuple[int, int, str]]:
    """(inicio_ms, fin_ms, título). Se acumulan muestras exactas para que no se desfasen."""
    marks, cum = [], 0
    for ch in chapters:
        start = round(1000 * cum / ch.sample_rate)
        cum += ch.frames
        marks.append((start, round(1000 * cum / ch.sample_rate), ch.title))
    return marks


def ffmetadata(job: dict[str, Any], chapters: list[ChapterAudio]) -> str:
    b = job["book"]
    lines = [";FFMETADATA1", f"title={_esc(b['title'])}", f"artist={_esc(b['author'])}",
             f"album_artist={_esc(b['author'])}", f"album={_esc(b['title'])}", "genre=Audiobook",
             "comment=AudioLibro Libre"]
    for start, end, title in chapter_marks(chapters):
        lines += ["[CHAPTER]", "TIMEBASE=1/1000", f"START={start}", f"END={end}", f"title={_esc(title)}"]
    return "\n".join(lines) + "\n"


def export_m4b(job: dict[str, Any], chapters: list[ChapterAudio], out_dir: Path, work: Path) -> Path:
    """Une los capítulos, normaliza el volumen una sola vez para todo el libro y escribe el .m4b."""
    out = out_dir / f"{safe_name(job['book']['title'])}.m4b"
    out.unlink(missing_ok=True)
    listing = work / "concat.txt"
    listing.write_text("".join(f"file '{ch.wav.name}'\n" for ch in chapters), encoding="utf-8")
    meta = work / "chapters.ffmeta"
    meta.write_text(ffmetadata(job, chapters), encoding="utf-8")
    cover = cover_path(job)
    cmd = ["-f", "concat", "-safe", "0", "-i", str(listing)]
    if cover:
        cmd += ["-i", str(cover)]
    meta_idx = 2 if cover else 1
    cmd += ["-i", str(meta), "-map", "0:a"]
    if cover:
        cmd += ["-map", "1:v", "-c:v", "copy", "-disposition:v:0", "attached_pic"]
    cmd += ["-map_metadata", str(meta_idx), "-map_chapters", str(meta_idx),
            "-af", LOUDNORM, "-ac", "1", "-ar", "44100", "-c:a", "aac", "-b:a", "64k",
            "-movflags", "+faststart", "-f", "mp4", str(out)]
    run_ffmpeg(cmd)
    return out
