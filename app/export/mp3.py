"""Exportación a MP3 por capítulo (ffmpeg por subprocess: normalización, ID3 y portada) y ZIP."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import threading
import unicodedata
import zipfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from app.errors import UserError
from app.export.metadata import credits_text, id3_args
from app.jobs.audio_io import assemble
from app.jobs.runner import build_plan
from app.jobs.store import chunk_dir, job_path

# Volumen homogéneo entre capítulos (voz hablada). TP=-2.5: el códec (AAC/MP3) añade hasta ~1 dB de
# sobrepico al decodificar; con -1.5 el M4B de 8 h medido llegó a +1,1 dBFS (saturaba).
LOUDNORM = "loudnorm=I=-19:TP=-2.5:LRA=11"
WORKERS = max(1, min(4, os.cpu_count() or 1))


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


def render_chapter_wavs(job: dict[str, Any], work: Path,
                        progress: Callable[[str], None] | None = None) -> list[tuple[str, Path]]:
    """Monta cada capítulo incluido en un WAV (fragmentos + pausas). Es el paso común a MP3 y M4B."""
    gaps = missing_chunks(job)
    if gaps:
        raise UserError("export_incomplete", missing=gaps)
    s = job["settings"]
    out = []
    for n, pc in enumerate(build_plan(job), 1):
        if progress:
            progress(pc.title)
        wav = work / f"{n:03d}.wav"
        assemble(pc.chunks, chunk_dir(job["id"], pc.id), wav,
                 pause_paragraph=float(s["pause_paragraph"]), pause_chapter=float(s["pause_chapter"]))
        out.append((pc.title, wav))
    return out


def encode_mp3(job: dict[str, Any], n: int, total: int, title: str, wav: Path, out_dir: Path) -> Path:
    """MP3 de un capítulo ya normalizado (`wav` puede ser WAV o FLAC)."""
    b = job["book"]
    cover = cover_path(job)
    out = out_dir / f"{n:02d} - {safe_name(title)}.mp3"
    cmd = ["-i", str(wav)]
    if cover:
        cmd += ["-i", str(cover)]
    cmd += ["-map", "0:a"] + (["-map", "1:v", "-c:v", "copy", "-metadata:s:v", "title=Cover",
                               "-metadata:s:v", "comment=Cover (front)"] if cover else [])
    cmd += ["-ac", "1", "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "64k",
            "-id3v2_version", "3", "-write_id3v1", "1",
            *id3_args(title=title, artist=b["author"], album=b["title"], track=n, tracks=total,
                      comment="AudioLibro Libre"),
            str(out)]
    run_ffmpeg(cmd)
    return out


def export_mp3(job: dict[str, Any], progress: Callable[[int, int, str], None] | None = None) -> list[Path]:
    """Solo MP3 (un archivo por capítulo). `export_all` genera además el M4B."""
    return export_all(job, ["mp3"], progress)["mp3"]


def normalize_chapter(wav: Path) -> Path:
    """Normaliza el volumen de un capítulo a FLAC (sin pérdida, mitad de tamaño) y borra el WAV."""
    out = wav.with_suffix(".flac")
    run_ffmpeg(["-i", str(wav), "-af", LOUDNORM, "-ac", "1", "-c:a", "flac", str(out)])
    wav.unlink()
    return out


def _parallel(fn: Callable[..., Any], jobs: list[tuple], tick: Callable[[str], None] | None,
              labels: list[str]) -> list[Any]:
    """Ejecuta `fn(*args)` en varios hilos (cada uno lanza un ffmpeg) conservando el orden."""
    lock = threading.Lock()

    def run(i: int) -> Any:
        res = fn(*jobs[i])
        if tick:
            with lock:
                tick(labels[i])
        return res

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        return list(pool.map(run, range(len(jobs))))


def export_all(job: dict[str, Any], formats: list[str],
               progress: Callable[[int, int, str], None] | None = None) -> dict[str, Any]:
    """Genera los formatos pedidos ("mp3", "m4b"). Devuelve {"mp3": [Path…], "m4b": Path | None}.

    Cada capítulo se monta y normaliza una sola vez (en paralelo); de ese FLAC salen los MP3 y el M4B.
    """
    from app.export.m4b import export_m4b, measure

    if not formats or not set(formats) <= {"mp3", "m4b"}:
        raise UserError("export_format_none")
    out_dir = export_dir(job["id"])
    for old in [*out_dir.glob("*.mp3"), *out_dir.glob("*.m4b"), *out_dir.glob("*.zip")]:
        old.unlink()
    n_ch = len([c for c in job["book"]["chapters"] if c["included"]])
    total = n_ch * (2 + ("mp3" in formats)) + ("m4b" in formats)
    done = [0]

    def tick(label: str) -> None:
        if progress:
            progress(done[0], total, label)
        done[0] += 1

    result: dict[str, Any] = {"mp3": [], "m4b": None}
    with tempfile.TemporaryDirectory(dir=out_dir) as tmp:
        work = Path(tmp)
        wavs = render_chapter_wavs(job, work, tick)
        titles = [t for t, _ in wavs]
        flacs = _parallel(normalize_chapter, [(w,) for _, w in wavs], tick, titles)
        if "mp3" in formats:
            args = [(job, n, len(flacs), titles[n - 1], flacs[n - 1], out_dir) for n in range(1, len(flacs) + 1)]
            result["mp3"] = _parallel(encode_mp3, args, tick, titles)
        if "m4b" in formats:
            tick(job["book"]["title"])
            result["m4b"] = export_m4b(job, [measure(t, f) for t, f in zip(titles, flacs, strict=True)],
                                       out_dir, work)
    if progress:
        progress(total, total, "")
    return result


def make_zip(job: dict[str, Any], files: list[Path], m4b: Path | None = None) -> Path:
    out = export_dir(job["id"]) / f"{safe_name(job['book']['title'])}.zip"
    out.unlink(missing_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as z:   # los MP3 ya están comprimidos
        for f in files:
            z.write(f, f.name)
        if m4b is not None:
            z.write(m4b, m4b.name)
        cover = cover_path(job)
        if cover:
            z.write(cover, f"portada{cover.suffix}")
        z.writestr("CREDITOS.txt", credits_text(job))
    return out
