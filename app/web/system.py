"""Comprobaciones del sistema: herramientas instaladas, disco y memoria."""
from __future__ import annotations

import os
import shutil
from typing import Any

from app.config import data_dir
from app.tts.phonemize import espeak_binary


def total_ram() -> int:
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (ValueError, OSError, AttributeError):
        pass
    try:  # Windows
        import ctypes

        class _Mem(ctypes.Structure):
            _fields_ = [("l", ctypes.c_ulong), ("p", ctypes.c_ulong), ("total", ctypes.c_ulonglong),
                        ("a", ctypes.c_ulonglong), ("tp", ctypes.c_ulonglong), ("ap", ctypes.c_ulonglong),
                        ("tv", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong), ("e", ctypes.c_ulonglong)]

        m = _Mem()
        m.l = ctypes.sizeof(_Mem)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))  # type: ignore[attr-defined]
        return int(m.total)
    except Exception:
        return 0


def system_info() -> dict[str, Any]:
    return {
        "ffmpeg": bool(shutil.which("ffmpeg")),
        "espeak": bool(espeak_binary()),
        "tesseract": bool(shutil.which("tesseract")),
        "disk_free_bytes": shutil.disk_usage(data_dir()).free,
        "ram_total_bytes": total_ram(),
        "cpu_count": os.cpu_count() or 1,
    }
