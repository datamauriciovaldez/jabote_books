"""Motor de voz falso para probar la cola sin descargar modelos."""
from __future__ import annotations

import threading
import time

import numpy as np

from app.tts.base import Audio, TTSEngine, VoiceInfo


class FakeEngine(TTSEngine):
    id = "piper"
    name = "Fake"

    def __init__(self, delay: float = 0.0, fail_on: str | None = None) -> None:
        self.calls: list[str] = []
        self.delay = delay
        self.fail_on = fail_on
        self.installed = {"fake-voice"}

    def list_voices(self, lang=None):
        return [VoiceInfo("fake-voice", "piper", "es", "es_ES", "fake", "low", 1, "CC0-1.0", False, "", 1000, True)]

    def voice_info(self, voice_id):
        lang = "en" if voice_id.startswith("en") else "es"
        return VoiceInfo(voice_id, "piper", lang, f"{lang}_XX", voice_id, "low", 1, "CC0-1.0", False, "", 1000,
                         voice_id in self.installed)

    def is_installed(self, voice_id):
        return voice_id in self.installed

    def install(self, voice_id, progress=None, cancel=None):
        self.installed.add(voice_id)

    def synthesize(self, text, voice_id, *, speed=1.0, speaker=0):
        if self.delay:
            time.sleep(self.delay)
        if self.fail_on and self.fail_on in text:
            raise RuntimeError("boom")
        self.calls.append(text)
        n = int(22050 * max(0.2, len(text) / 15 / speed))
        t = np.arange(n) / 22050
        return Audio((0.3 * np.sin(2 * np.pi * 220 * t)).astype(np.float32), 22050)


_ = threading  # noqa: F401
