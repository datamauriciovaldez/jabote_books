"""Ejecuta la exportación en segundo plano y expone su estado a la interfaz."""
from __future__ import annotations

import threading
from typing import Any

from app.errors import Conflict, UserError
from app.export.mp3 import export_all, export_dir, make_zip
from app.jobs.store import load_job

_state: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def status(job_id: str) -> dict[str, Any]:
    st = _state.get(job_id)
    if st:
        return dict(st)
    d = export_dir(job_id)
    zips = list(d.glob("*.zip"))
    if zips:
        m4b = next(iter(d.glob("*.m4b")), None)
        return {"state": "done", "done": 1, "total": 1, "current": "", "error": None,
                "files": sorted(p.name for p in d.glob("*.mp3")), "zip": zips[0].name,
                "m4b": m4b.name if m4b else None}
    return {"state": "idle", "done": 0, "total": 0, "current": "", "error": None, "files": [], "zip": None,
            "m4b": None}


def start(job_id: str, formats: list[str] | None = None) -> None:
    formats = formats or ["mp3", "m4b"]
    job = load_job(job_id)
    with _lock:
        if _state.get(job_id, {}).get("state") == "running":
            raise Conflict("export_already_running")
        _state[job_id] = {"state": "running", "done": 0, "total": 0, "current": "", "error": None,
                          "files": [], "zip": None, "m4b": None}

    def progress(done: int, total: int, current: str) -> None:
        _state[job_id].update(done=done, total=total, current=current)

    def work() -> None:
        try:
            res = export_all(job, formats, progress)
            zip_path = make_zip(job, res["mp3"], res["m4b"])
            _state[job_id].update(state="done", files=[f.name for f in res["mp3"]], zip=zip_path.name,
                                  m4b=res["m4b"].name if res["m4b"] else None)
        except UserError as exc:
            _state[job_id].update(state="error", error={"code": exc.code, "detail": exc.detail,
                                                        "params": exc.params})
        except Exception as exc:  # pragma: no cover
            _state[job_id].update(state="error", error={"code": "unexpected", "detail": str(exc), "params": {}})

    threading.Thread(target=work, name=f"export-{job_id}", daemon=True).start()
