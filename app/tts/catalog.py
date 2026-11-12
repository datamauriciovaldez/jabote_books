"""Catálogo de voces de Piper (solo licencias permisivas; generado por tools/audit_voices.py)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.config import HF_BASE
from app.errors import NotFound
from app.tts.base import VoiceInfo

_FILE = Path(__file__).with_name("voices.json")


@lru_cache(maxsize=1)
def _raw() -> dict[str, dict]:
    data = json.loads(_FILE.read_text(encoding="utf-8"))
    return {v["id"]: v for v in data["voices"]}


def get_raw(voice_id: str) -> dict:
    try:
        return _raw()[voice_id]
    except KeyError as exc:
        raise NotFound("voice_unknown", voice=voice_id) from exc


def all_voices(engine: str = "piper") -> list[VoiceInfo]:
    return [
        VoiceInfo(
            id=v["id"], engine=engine, lang=v["lang"], locale=v["locale"], name=v["name"],
            quality=v["quality"], speakers=v["speakers"], license=v["license"],
            attribution_required=v["attribution_required"], dataset_url=v["dataset_url"],
            size_bytes=v["size_bytes"],
        )
        for v in _raw().values()
    ]


def file_url(voice_id: str, suffix: str) -> str:
    """URL de descarga (.onnx o .onnx.json) en Hugging Face."""
    return f"{HF_BASE}/{get_raw(voice_id)['path']}{suffix}"
