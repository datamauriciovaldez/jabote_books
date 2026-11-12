"""API HTTP local. Todos los errores salen como {"error": {code, detail, params}} y la interfaz los traduce."""
from __future__ import annotations

import io
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from app import tts
from app.errors import NotFound, UserError
from app.export import manager as export_manager
from app.export.mp3 import export_dir, safe_name
from app.extractors.base import SUPPORTED, extract
from app.jobs import estimate as est
from app.jobs.audio_io import assemble
from app.jobs.runner import runner
from app.jobs.store import (
    chunk_dir,
    create_job,
    delete_job,
    job_path,
    list_jobs,
    load_job,
    update_job,
)
from app.tts import catalog
from app.web.system import system_info

router = APIRouter(prefix="/api")
MAX_UPLOAD = 300 * 1024 * 1024
SAMPLES = {
    "es": "En un lugar de la Mancha, de cuyo nombre no quiero acordarme, no ha mucho tiempo que vivía un "
          "hidalgo de los de lanza en astillero, adarga antigua, rocín flaco y galgo corredor. "
          "Una olla de algo más vaca que carnero, salpicón las más noches, duelos y quebrantos los sábados.",
    "en": "It is a truth universally acknowledged, that a single man in possession of a good fortune, must be "
          "in want of a wife. However little known the feelings or views of such a man may be on his first "
          "entering a neighbourhood, this truth is so well fixed in the minds of the surrounding families.",
}
SAMPLE_SECONDS = 10.0


# ------------------------------------------------------------------- esquemas
class PronRule(BaseModel):
    source: str = Field(max_length=100)
    spoken: str = Field(max_length=200)
    whole_word: bool = True
    case_sensitive: bool = True


class SettingsIn(BaseModel):
    engine: str = "piper"
    voice: str = ""
    speaker: int = Field(0, ge=0, le=2000)
    speed: float = Field(1.0, ge=0.5, le=2.0)
    pause_paragraph: float = Field(0.7, ge=0, le=5)
    pause_chapter: float = Field(2.0, ge=0, le=15)
    read_titles: bool = True
    pronunciation: list[PronRule] = []


class ChapterIn(BaseModel):
    id: int | None = None
    title: str = Field(max_length=300)
    text: str
    included: bool = True


class BookIn(BaseModel):
    title: str = Field(max_length=300)
    author: str = Field("", max_length=300)
    language: str = Field("es", pattern="^(es|en)$")
    chapters: list[ChapterIn]


class SampleIn(BaseModel):
    speed: float = Field(1.0, ge=0.5, le=2.0)
    speaker: int = 0
    text: str = Field("", max_length=1000)


# --------------------------------------------------------------------- sistema
@router.get("/system")
def system() -> dict[str, Any]:
    info = system_info()
    info["engines"] = {e: tts.get_engine(e).problems() for e in tts.available_engines()}
    info["supported_formats"] = list(SUPPORTED)
    return info


# ----------------------------------------------------------------------- voces
_installs: dict[str, dict[str, Any]] = {}


@router.get("/voices")
def voices(lang: str | None = None, engine: str = "piper") -> list[dict[str, Any]]:
    return [v.__dict__ for v in tts.get_engine(engine).list_voices(lang)]


@router.post("/voices/{voice_id}/install")
def install_voice(voice_id: str, engine: str = "piper") -> dict[str, Any]:
    eng = tts.get_engine(engine)
    catalog.get_raw(voice_id)
    if eng.is_installed(voice_id):
        return {"state": "done", "done": 1, "total": 1}
    if _installs.get(voice_id, {}).get("state") == "running":
        return _installs[voice_id]
    st = {"state": "running", "done": 0, "total": catalog.get_raw(voice_id)["size_bytes"], "error": None}
    _installs[voice_id] = st

    def work() -> None:
        try:
            eng.install(voice_id, lambda d, t: st.update(done=d, total=t or st["total"]))
            st.update(state="done", done=st["total"])
        except UserError as exc:
            st.update(state="error", error={"code": exc.code, "detail": exc.detail, "params": exc.params})
        except Exception as exc:  # pragma: no cover
            st.update(state="error", error={"code": "unexpected", "detail": str(exc), "params": {}})

    threading.Thread(target=work, daemon=True, name=f"install-{voice_id}").start()
    return st


@router.get("/voices/{voice_id}/install")
def install_status(voice_id: str, engine: str = "piper") -> dict[str, Any]:
    if tts.get_engine(engine).is_installed(voice_id):
        return {"state": "done", "done": 1, "total": 1, "error": None}
    return _installs.get(voice_id, {"state": "idle", "done": 0, "total": 0, "error": None})


@router.post("/voices/{voice_id}/sample")
def voice_sample(voice_id: str, body: SampleIn, engine: str = "piper") -> Response:
    """Muestra de 10 segundos de la voz (sin tocar el libro)."""
    eng = tts.get_engine(engine)
    if probs := eng.problems():
        raise UserError(probs[0])
    lang = catalog.get_raw(voice_id)["lang"]
    text = body.text.strip() or SAMPLES[lang]
    audio = eng.synthesize(text, voice_id, speed=body.speed, speaker=body.speaker)
    n = min(len(audio.samples), int(SAMPLE_SECONDS * audio.sample_rate))
    samples = audio.samples[:n].copy()
    fade = min(n, int(0.25 * audio.sample_rate))
    if fade:
        samples[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
    buf = io.BytesIO()
    sf.write(buf, samples, audio.sample_rate, format="WAV", subtype="PCM_16")
    return Response(buf.getvalue(), media_type="audio/wav")


# ------------------------------------------------------------------- proyectos
def _public(job: dict[str, Any]) -> dict[str, Any]:
    out = dict(job)
    out["has_cover"] = bool(job["book"].get("cover"))
    return out


@router.post("/jobs")
def upload(file: UploadFile = File(...), language: str = Form("")) -> dict[str, Any]:
    name = Path(file.filename or "libro").name
    ext = Path(name).suffix.lower()
    if ext not in SUPPORTED:
        raise UserError("unsupported_format", ext=ext or "?", supported=", ".join(SUPPORTED))
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / f"upload{ext}"
        size = 0
        with dest.open("wb") as fh:
            while block := file.file.read(1 << 20):
                size += len(block)
                if size > MAX_UPLOAD:
                    raise UserError("file_too_big", max_mb=MAX_UPLOAD // (1024 * 1024))
                fh.write(block)
        book = extract(dest)
        if book.title in ("upload", ""):
            book.title = Path(name).stem
    return _public(create_job(book, name, language if language in ("es", "en") else ""))


@router.post("/jobs/demo")
def demo(lang: str = "es") -> dict[str, Any]:
    """Crea un proyecto con el libro de ejemplo (dominio público) para el tutorial."""
    sample = Path(__file__).resolve().parents[1] / "samples" / ("pride.txt" if lang == "en" else "quijote.txt")
    return _public(create_job(extract(sample), sample.name, "en" if lang == "en" else "es"))


@router.get("/jobs")
def jobs() -> list[dict[str, Any]]:
    return list_jobs()


@router.get("/jobs/{job_id}")
def job(job_id: str) -> dict[str, Any]:
    return _public(load_job(job_id))


@router.delete("/jobs/{job_id}")
def remove(job_id: str) -> dict[str, bool]:
    load_job(job_id)
    if load_job(job_id)["state"]["status"] in ("running", "queued"):
        raise UserError("job_running")
    delete_job(job_id)
    return {"ok": True}


@router.put("/jobs/{job_id}/book")
def save_book(job_id: str, body: BookIn) -> dict[str, Any]:
    if not body.chapters:
        raise UserError("no_chapters")

    def mutate(j: dict[str, Any]) -> None:
        used = {c.id for c in body.chapters if c.id}
        nxt = max([0, *used, *(c["id"] for c in j["book"]["chapters"])]) + 1
        chapters = []
        for c in body.chapters:
            cid = c.id
            if cid is None:
                cid, nxt = nxt, nxt + 1
            chapters.append({"id": cid, "title": c.title.strip(), "text": c.text, "included": c.included})
        j["book"].update(title=body.title.strip(), author=body.author.strip(), language=body.language,
                         chapters=chapters)
        if j["state"]["status"] == "done":
            j["state"]["status"] = "idle"

    if load_job(job_id)["state"]["status"] in ("running", "queued"):
        raise UserError("job_running")
    return _public(update_job(job_id, mutate))


@router.put("/jobs/{job_id}/settings")
def save_settings(job_id: str, body: SettingsIn) -> dict[str, Any]:
    if load_job(job_id)["state"]["status"] in ("running", "queued"):
        raise UserError("job_running")
    tts.get_engine(body.engine)
    if body.voice:
        catalog.get_raw(body.voice)
    return _public(update_job(job_id, lambda j: j["settings"].update(body.model_dump())))


@router.get("/jobs/{job_id}/estimate")
def estimate(job_id: str) -> dict[str, Any]:
    j = load_job(job_id)
    plan = runner.plan(j)
    sizes = [pc.chars for pc in plan]
    voice_size = catalog.get_raw(j["settings"]["voice"])["size_bytes"] if j["settings"]["voice"] else 63_000_000
    e = est.estimate(sum(sizes), max(sizes, default=0), speed=float(j["settings"]["speed"]),
                     voice_size_bytes=voice_size)
    e["chapters"] = len(plan)
    e["system"] = system_info()
    return e


@router.post("/jobs/{job_id}/start")
def start(job_id: str) -> dict[str, Any]:
    runner.start(job_id)
    return runner.progress(job_id)


@router.post("/jobs/{job_id}/pause")
def pause(job_id: str) -> dict[str, bool]:
    runner.stop(job_id, "pause")
    return {"ok": True}


@router.post("/jobs/{job_id}/cancel")
def cancel(job_id: str) -> dict[str, bool]:
    runner.stop(job_id, "cancel")
    return {"ok": True}


@router.get("/jobs/{job_id}/progress")
def progress(job_id: str) -> dict[str, Any]:
    return runner.progress(job_id)


@router.get("/jobs/{job_id}/chapters/{chapter_id}/preview")
def preview(job_id: str, chapter_id: int, seconds: float = 45.0) -> Response:
    """Audio ya generado de un capítulo (hasta `seconds`), para escucharlo mientras se procesa."""
    j = load_job(job_id)
    pc = next((p for p in runner.plan(j) if p.id == chapter_id), None)
    if pc is None:
        raise NotFound("chapter_not_found")
    buf = io.BytesIO()
    secs = assemble(pc.chunks, chunk_dir(job_id, chapter_id), buf, pause_paragraph=float(
        j["settings"]["pause_paragraph"]), max_seconds=min(max(seconds, 5.0), 180.0))
    if secs <= 0:
        raise NotFound("preview_empty")
    return Response(buf.getvalue(), media_type="audio/wav")


@router.post("/jobs/{job_id}/cover")
def set_cover(job_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
    head = file.file.read(12)
    ext = ".png" if head.startswith(b"\x89PNG") else ".jpg" if head.startswith(b"\xff\xd8") else None
    if ext is None:
        raise UserError("cover_invalid")
    file.file.seek(0)
    root = job_path(load_job(job_id)["id"])
    for old in root.glob("cover.*"):
        old.unlink()
    with (root / f"cover{ext}").open("wb") as fh:
        shutil.copyfileobj(file.file, fh)
    return _public(update_job(job_id, lambda j: j["book"].update(cover=f"cover{ext}")))


@router.get("/jobs/{job_id}/cover")
def get_cover(job_id: str) -> FileResponse:
    name = load_job(job_id)["book"].get("cover")
    if not name:
        raise NotFound("cover_missing")
    return FileResponse(job_path(job_id) / name)


# ------------------------------------------------------------------- exportar
@router.post("/jobs/{job_id}/export")
def start_export(job_id: str) -> dict[str, Any]:
    export_manager.start(job_id)
    return export_manager.status(job_id)


@router.get("/jobs/{job_id}/export")
def export_status(job_id: str) -> dict[str, Any]:
    load_job(job_id)
    return export_manager.status(job_id)


@router.get("/jobs/{job_id}/download/{name}")
def download(job_id: str, name: str) -> FileResponse:
    load_job(job_id)
    f = export_dir(job_id) / Path(name).name
    if not f.is_file() or f.suffix not in (".zip", ".mp3", ".m4b"):
        raise NotFound("file_not_found")
    return FileResponse(f, filename=safe_name(f.stem, 120) + f.suffix)
