"""Descarga de ficheros con barra de progreso, verificación y escritura atómica."""
from __future__ import annotations

import hashlib
import threading
from pathlib import Path

import httpx

from app.errors import UserError
from app.tts.base import ProgressCb


def download_file(url: str, dest: Path, *, expected_size: int = 0, sha256: str = "",
                  progress: ProgressCb | None = None, cancel: threading.Event | None = None) -> None:
    """Descarga `url` en `dest`. Escribe en `.part` y renombra al terminar."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    digest = hashlib.sha256()
    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=httpx.Timeout(30, read=60)) as r:
            if r.status_code != 200:
                raise UserError("download_failed", f"HTTP {r.status_code}", url=url)
            total = int(r.headers.get("content-length") or expected_size or 0)
            done = 0
            with part.open("wb") as fh:
                for block in r.iter_bytes(1 << 20):
                    if cancel is not None and cancel.is_set():
                        raise UserError("download_cancelled")
                    fh.write(block)
                    digest.update(block)
                    done += len(block)
                    if progress:
                        progress(done, total)
    except httpx.HTTPError as exc:
        part.unlink(missing_ok=True)
        raise UserError("no_internet", str(exc), url=url) from exc
    except UserError:
        part.unlink(missing_ok=True)
        raise
    if expected_size and done != expected_size:
        part.unlink(missing_ok=True)
        raise UserError("download_corrupt", f"{done} != {expected_size} bytes")
    if sha256 and digest.hexdigest() != sha256:
        part.unlink(missing_ok=True)
        raise UserError("download_corrupt", "sha256 distinto")
    part.replace(dest)
