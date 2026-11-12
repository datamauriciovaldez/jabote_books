"""Registro de motores de voz. Para añadir uno, regístralo en `_FACTORIES`."""
from __future__ import annotations

from collections.abc import Callable

from app.errors import NotFound
from app.tts.base import Audio, TTSEngine, VoiceInfo

__all__ = ["Audio", "TTSEngine", "VoiceInfo", "available_engines", "get_engine"]


def _piper() -> TTSEngine:
    from app.tts.piper import PiperEngine

    return PiperEngine()


_FACTORIES: dict[str, Callable[[], TTSEngine]] = {"piper": _piper}
_INSTANCES: dict[str, TTSEngine] = {}


def available_engines() -> list[str]:
    return list(_FACTORIES)


def get_engine(engine_id: str) -> TTSEngine:
    if engine_id not in _FACTORIES:
        raise NotFound("engine_unknown", engine=engine_id)
    if engine_id not in _INSTANCES:
        _INSTANCES[engine_id] = _FACTORIES[engine_id]()
    return _INSTANCES[engine_id]
