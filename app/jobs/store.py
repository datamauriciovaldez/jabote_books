"""Estado de los proyectos en disco (JSON atómico). Cada proyecto vive en data/jobs/<id>/."""
from __future__ import annotations

import json
import os
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from app.config import jobs_dir
from app.errors import NotFound
from app.extractors.base import Book

DEFAULT_SETTINGS: dict[str, Any] = {
    "engine": "piper", "voice": "", "speaker": 0, "speed": 1.0,
    "pause_paragraph": 0.7, "pause_chapter": 2.0, "read_titles": True, "pronunciation": [],
}
_lock = threading.RLock()


def job_path(job_id: str) -> Path:
    if not job_id.isalnum():
        raise NotFound("job_not_found", job=job_id)
    return jobs_dir() / job_id


def create_job(book: Book, source_name: str, language: str = "") -> dict[str, Any]:
    job_id = uuid.uuid4().hex[:12]
    root = job_path(job_id)
    root.mkdir(parents=True)
    cover_name = None
    if book.cover:
        cover_name = "cover" + (".png" if "png" in book.cover_mime else ".jpg")
        (root / cover_name).write_bytes(book.cover)
    job = {
        "id": job_id, "created": time.time(), "updated": time.time(), "source_name": source_name,
        "book": {
            "title": book.title, "author": book.author, "language": language or book.language or "es",
            "cover": cover_name,
            "chapters": [{"id": i + 1, "title": c.title, "text": c.text, "included": c.included}
                         for i, c in enumerate(book.chapters)],
        },
        "settings": dict(DEFAULT_SETTINGS),
        "state": {"status": "idle", "error": None},
        "warnings": list(book.warnings),
    }
    save_job(job)
    return job


def load_job(job_id: str) -> dict[str, Any]:
    f = job_path(job_id) / "job.json"
    if not f.exists():
        raise NotFound("job_not_found", job=job_id)
    with _lock:
        return json.loads(f.read_text(encoding="utf-8"))


def save_job(job: dict[str, Any]) -> None:
    job["updated"] = time.time()
    root = job_path(job["id"])
    tmp = root / "job.json.tmp"
    with _lock:
        tmp.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, root / "job.json")


def update_job(job_id: str, mutate) -> dict[str, Any]:
    """Lee-modifica-guarda bajo candado (la interfaz y el trabajador escriben a la vez)."""
    with _lock:
        job = load_job(job_id)
        mutate(job)
        save_job(job)
        return job


def list_jobs() -> list[dict[str, Any]]:
    out = []
    for d in sorted(jobs_dir().iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        f = d / "job.json"
        if f.exists():
            try:
                j = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            out.append({"id": j["id"], "title": j["book"]["title"], "author": j["book"]["author"],
                        "updated": j["updated"], "status": j["state"]["status"],
                        "chapters": len(j["book"]["chapters"])})
    return out


def delete_job(job_id: str) -> None:
    shutil.rmtree(job_path(job_id), ignore_errors=True)


def chunk_dir(job_id: str, chapter_id: int) -> Path:
    d = job_path(job_id) / "chunks" / f"{chapter_id:03d}"
    d.mkdir(parents=True, exist_ok=True)
    return d
