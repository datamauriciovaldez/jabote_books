"""Cola de trabajos en proceso (un hilo, sin Redis ni Celery) con pausa, cancelación y reanudación.

Cada fragmento se guarda en disco al terminar. Reanudar = volver a empezar: los que ya existen se saltan.
"""
from __future__ import annotations

import hashlib
import json
import logging
import queue
import threading
import time
from dataclasses import dataclass
from typing import Any

from app import tts
from app.cleaning.pronunciation import parse_rules
from app.errors import Conflict, UserError
from app.jobs import estimate as est
from app.jobs.audio_io import save_chunk
from app.jobs.chunking import Chunk, chapter_chunks, synthesis_signature
from app.jobs.store import chunk_dir, load_job, update_job

log = logging.getLogger(__name__)


@dataclass
class PlanChapter:
    id: int
    title: str
    chunks: list[Chunk]

    @property
    def chars(self) -> int:
        return sum(len(c.text) for c in self.chunks)


def build_plan(job: dict[str, Any]) -> list[PlanChapter]:
    """Fragmentos de todos los capítulos incluidos, según los ajustes actuales."""
    s = job["settings"]
    sig = synthesis_signature(s["engine"], s["voice"], int(s["speaker"]), float(s["speed"]))
    rules = parse_rules(s.get("pronunciation", []))
    return [
        PlanChapter(c["id"], c["title"], chapter_chunks(
            c["id"], c["title"], c["text"], signature=sig, read_title=bool(s["read_titles"]), rules=rules))
        for c in job["book"]["chapters"] if c["included"]
    ]


class JobRunner:
    def __init__(self) -> None:
        self._q: queue.Queue[str] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._ctl: dict[str, dict[str, Any]] = {}
        self._live: dict[str, dict[str, Any]] = {}
        self._plans: dict[str, tuple[str, list[PlanChapter]]] = {}

    # ------------------------------------------------------------- plan / progreso
    def plan(self, job: dict[str, Any]) -> list[PlanChapter]:
        sig = hashlib.sha256(json.dumps([job["book"]["chapters"], job["settings"]],
                                      sort_keys=True).encode()).hexdigest()
        cached = self._plans.get(job["id"])
        if cached and cached[0] == sig:
            return cached[1]
        plan = build_plan(job)
        self._plans[job["id"]] = (sig, plan)
        return plan

    def progress(self, job_id: str) -> dict[str, Any]:
        job = load_job(job_id)
        plan = self.plan(job)
        chapters, done_total, total, remaining_chars = [], 0, 0, 0
        for pc in plan:
            d = chunk_dir(job_id, pc.id)
            done = 0
            for ch in pc.chunks:
                if (d / ch.filename).exists():
                    done += 1
                else:
                    remaining_chars += len(ch.text)
            chapters.append({"id": pc.id, "title": pc.title, "total": len(pc.chunks), "done": done})
            done_total += done
            total += len(pc.chunks)
        live = self._live.get(job_id)
        status = job["state"]["status"]
        eta = None
        if status == "running":
            if live and live["chars"] > 200:
                eta = remaining_chars * (live["synth_seconds"] / live["chars"])
            else:
                speed = float(job["settings"]["speed"])
                rtf = est.measured_rtf(job["settings"]["voice"]) or est.DEFAULT_RTF
                eta = remaining_chars / (est.CHARS_PER_SECOND * speed * rtf)
        return {
            "status": status, "error": job["state"].get("error"), "total_chunks": total,
            "done_chunks": done_total, "percent": round(100 * done_total / total, 1) if total else 0.0,
            "chapters": chapters, "eta_seconds": round(eta) if eta is not None else None,
            "current_chapter": live["chapter"] if live and status == "running" else None,
            "elapsed_seconds": round(time.monotonic() - live["t0"]) if live and status == "running" else 0,
        }

    # -------------------------------------------------------------------- control
    def start(self, job_id: str) -> None:
        """Pone el proyecto en cola (o lo reanuda si ya había trabajo hecho)."""
        job = load_job(job_id)
        if job["state"]["status"] in ("running", "queued"):
            raise Conflict("job_already_running")
        s = job["settings"]
        if not s.get("voice"):
            raise UserError("voice_not_selected")
        engine = tts.get_engine(s["engine"])
        if (probs := engine.problems()):
            raise UserError(probs[0])
        if not engine.is_installed(s["voice"]):
            raise UserError("voice_not_installed", voice=s["voice"])
        if not any(c["included"] for c in job["book"]["chapters"]):
            raise UserError("no_chapters_selected")
        self._ctl[job_id] = {"stop": threading.Event(), "mode": "pause"}
        update_job(job_id, lambda j: j["state"].update(status="queued", error=None))
        self._q.put(job_id)
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._worker, name="audiolibro-worker", daemon=True)
                self._thread.start()

    def stop(self, job_id: str, mode: str) -> None:
        """mode: 'pause' o 'cancel'. Se detiene al terminar el fragmento en curso; nada se pierde."""
        ctl = self._ctl.get(job_id)
        status = load_job(job_id)["state"]["status"]
        if status not in ("running", "queued") or ctl is None:
            raise Conflict("job_not_running")
        ctl["mode"] = mode
        ctl["stop"].set()

    def recover(self) -> None:
        """Al arrancar la app: lo que quedó 'running' por un cierre brusco pasa a 'paused'."""
        from app.jobs.store import list_jobs

        for j in list_jobs():
            if j["status"] in ("running", "queued"):
                update_job(j["id"], lambda x: x["state"].update(status="paused"))

    def join(self, job_id: str, timeout: float = 30.0) -> str:
        """Espera (tests) hasta que el proyecto deje de estar en cola/ejecución."""
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            st = load_job(job_id)["state"]["status"]
            if st not in ("running", "queued"):
                return st
            time.sleep(0.02)
        raise TimeoutError(job_id)

    # --------------------------------------------------------------------- hilo
    def _worker(self) -> None:
        while True:
            try:
                job_id = self._q.get(timeout=300)
            except queue.Empty:
                return
            try:
                self._execute(job_id)
            except Exception:  # pragma: no cover - red de seguridad
                log.exception("fallo inesperado en el trabajador")

    def _execute(self, job_id: str) -> None:
        ctl = self._ctl[job_id]
        update_job(job_id, lambda j: j["state"].update(status="running", error=None))
        live = {"t0": time.monotonic(), "chars": 0, "synth_seconds": 0.0, "chapter": None}
        self._live[job_id] = live
        try:
            job = load_job(job_id)
            s = job["settings"]
            engine = tts.get_engine(s["engine"])
            plan = self.plan(job)
            self._prune(job_id, plan)
            for pc in plan:
                live["chapter"] = pc.id
                d = chunk_dir(job_id, pc.id)
                for ch in pc.chunks:
                    if ctl["stop"].is_set():
                        break
                    target = d / ch.filename
                    if target.exists():
                        continue
                    t0 = time.monotonic()
                    audio = engine.synthesize(ch.text, s["voice"], speed=float(s["speed"]),
                                              speaker=int(s["speaker"]))
                    save_chunk(target, audio.samples, audio.sample_rate)
                    dt = time.monotonic() - t0
                    live["chars"] += len(ch.text)
                    live["synth_seconds"] += dt
                    est.record_rtf(s["voice"], audio.seconds, dt)
                if ctl["stop"].is_set():
                    break
            final = ("paused" if ctl["mode"] == "pause" else "cancelled") if ctl["stop"].is_set() else "done"
            update_job(job_id, lambda j: j["state"].update(status=final, error=None))
        except UserError as exc:
            err = {"code": exc.code, "detail": exc.detail, "params": exc.params}
            update_job(job_id, lambda j: j["state"].update(status="error", error=err))
        except Exception as exc:
            log.exception("error generando %s", job_id)
            err = {"code": "unexpected", "detail": f"{type(exc).__name__}: {exc}", "params": {}}
            update_job(job_id, lambda j: j["state"].update(status="error", error=err))
        finally:
            self._live.pop(job_id, None)

    @staticmethod
    def _prune(job_id: str, plan: list[PlanChapter]) -> None:
        """Borra fragmentos obsoletos (texto o ajustes cambiados) y restos de escrituras interrumpidas."""
        for pc in plan:
            keep = {c.filename for c in pc.chunks}
            for f in chunk_dir(job_id, pc.id).iterdir():
                if f.name not in keep:
                    f.unlink(missing_ok=True)


runner = JobRunner()
