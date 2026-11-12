"""Ejecuta la exportación en segundo plano y expone su estado a la interfaz."""
from __future__ import annotations

import threading
from typing import Any

from app.errors import Conflict, UserError
from app.export.mp3 import export_dir, export_mp3, make_zip
from app.jobs.store import load_job

_state: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def status(job_id: str) -> dict[str, Any]:
    st = _state.get(job_id)
    if st:
        return dict(st)
    zips = list(export_dir(job_id).glob("*.zip"))
    if zips:
        return {"state": "done", "done": 1, "total": 1, "current": "", "error": None,
                "files": sorted(p.name for p in export_dir(job_id).glob("*.mp3")), "zip": zips[0].name}
    return {"state": "idle", "done": 0, "total": 0, "current": "", "error": None, "files": [], "zip": None}


def start(job_id: str) -> None:
    job = load_job(job_id)
    with _lock:
        if _state.get(job_id, {}).get("state") == "running":
            raise Conflict("export_already_running")
        _state[job_id] = {"state": "running", "done": 0, "total": 0, "current": "", "error": None,
                          "files": [], "zip": None}

    def progress(done: int, total: int, current: str) -> None:
        _state[job_id].update(done=done, total=total, current=current)

    def work() -> None:
        try:
            files = export_mp3(job, progress)
            zip_path = make_zip(job, files)
            _state[job_id].update(state="done", files=[f.name for f in files], zip=zip_path.name)
        except UserError as exc:
            _state[job_id].update(state="error", error={"code": exc.code, "detail": exc.detail,
                                                        "params": exc.params})
        except Exception as exc:  # pragma: no cover
            _state[job_id].update(state="error", error={"code": "unexpected", "detail": str(exc), "params": {}})

    threading.Thread(target=work, name=f"export-{job_id}", daemon=True).start()
