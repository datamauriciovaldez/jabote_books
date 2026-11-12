"""Exportación a MP3 por capítulo (ffmpeg por subprocess: normalización, ID3 y portada) y ZIP."""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unicodedata
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.errors import UserError
from app.export.metadata import credits_text, id3_args
from app.jobs.audio_io import assemble
from app.jobs.runner import build_plan
from app.jobs.store import chunk_dir, job_path

LOUDNORM = "loudnorm=I=-19:TP=-1.5:LRA=11"   # volumen homogéneo entre capítulos (voz hablada)


def ffmpeg_path() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise UserError("ffmpeg_missing")
    return exe


def safe_name(text: str, limit: int = 80) -> str:
    t = unicodedata.normalize("NFKD", text)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^\w\s.-]", "", t).strip()
    t = re.sub(r"\s+", " ", t)
    return (t[:limit].strip(" .") or "libro")


def run_ffmpeg(args: list[str]) -> None:
    proc = subprocess.run([ffmpeg_path(), "-hide_banner", "-loglevel", "error", "-y", *args],
                          capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise UserError("ffmpeg_failed", proc.stderr.strip()[-400:])


def export_dir(job_id: str) -> Path:
    d = job_path(job_id) / "export"
    d.mkdir(exist_ok=True)
    return d


def missing_chunks(job: dict[str, Any]) -> int:
    n = 0
    for pc in build_plan(job):
        d = chunk_dir(job["id"], pc.id)
        n += sum(1 for c in pc.chunks if not (d / c.filename).exists())
    return n


def cover_path(job: dict[str, Any]) -> Path | None:
    name = job["book"].get("cover")
    p = job_path(job["id"]) / name if name else None
    return p if p and p.exists() else None


def export_mp3(job: dict[str, Any], progress: Callable[[int, int, str], None] | None = None) -> list[Path]:
    """Genera un MP3 por capítulo incluido. Requiere que todo el audio esté generado."""
    gaps = missing_chunks(job)
    if gaps:
        raise UserError("export_incomplete", missing=gaps)
    plan = build_plan(job)
    out_dir = export_dir(job["id"])
    for old in out_dir.glob("*.mp3"):
        old.unlink()
    s, b = job["settings"], job["book"]
    cover = cover_path(job)
    files: list[Path] = []
    with tempfile.TemporaryDirectory(dir=out_dir) as tmp:
        for n, pc in enumerate(plan, 1):
            if progress:
                progress(n - 1, len(plan), pc.title)
            wav = Path(tmp) / f"{n}.wav"
            assemble(pc.chunks, chunk_dir(job["id"], pc.id), wav,
                     pause_paragraph=float(s["pause_paragraph"]), pause_chapter=float(s["pause_chapter"]))
            out = out_dir / f"{n:02d} - {safe_name(pc.title)}.mp3"
            cmd = ["-i", str(wav)]
            if cover:
                cmd += ["-i", str(cover)]
            cmd += ["-map", "0:a"] + (["-map", "1:v", "-c:v", "copy",
                                       "-metadata:s:v", "title=Cover", "-metadata:s:v", "comment=Cover (front)"]
                                      if cover else [])
            cmd += ["-af", LOUDNORM, "-ac", "1", "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "64k",
                    "-id3v2_version", "3", "-write_id3v1", "1",
                    *id3_args(title=pc.title, artist=b["author"], album=b["title"], track=n, tracks=len(plan),
                              comment="AudioLibro Libre"),
                    str(out)]
            run_ffmpeg(cmd)
            files.append(out)
    if progress:
        progress(len(plan), len(plan), "")
    return files


def make_zip(job: dict[str, Any], files: list[Path]) -> Path:
    out = export_dir(job["id"]) / f"{safe_name(job['book']['title'])}.zip"
    out.unlink(missing_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as z:   # los MP3 ya están comprimidos
        for f in files:
            z.write(f, f.name)
        cover = cover_path(job)
        if cover:
            z.write(cover, f"portada{cover.suffix}")
        z.writestr("CREDITOS.txt", credits_text(job))
    return out
