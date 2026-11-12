"""Interfaz abstracta de motor de voz. Para añadir un motor: ver docs/ADDING_A_VOICE_ENGINE.md."""
from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

ProgressCb = Callable[[int, int], None]  # (bytes_hechos, bytes_totales)


@dataclass(frozen=True)
class VoiceInfo:
    """Voz disponible en el catálogo de un motor."""

    id: str
    engine: str
    lang: str            # "es" | "en"
    locale: str          # "es_ES"
    name: str
    quality: str
    speakers: int
    license: str
    attribution_required: bool
    dataset_url: str
    size_bytes: int
    installed: bool = False


@dataclass
class Audio:
    samples: np.ndarray  # float32 mono en [-1, 1]
    sample_rate: int

    @property
    def seconds(self) -> float:
        return len(self.samples) / self.sample_rate


class TTSEngine(ABC):
    """Contrato mínimo que cumple cualquier motor de síntesis."""

    id: str = ""
    name: str = ""

    @abstractmethod
    def list_voices(self, lang: str | None = None) -> list[VoiceInfo]:
        """Voces del catálogo (con `installed` informado)."""

    @abstractmethod
    def is_installed(self, voice_id: str) -> bool: ...

    @abstractmethod
    def install(self, voice_id: str, progress: ProgressCb | None = None,
                cancel: threading.Event | None = None) -> None:
        """Descarga la voz. Lanza UserError con mensaje humano si falla."""

    @abstractmethod
    def synthesize(self, text: str, voice_id: str, *, speed: float = 1.0, speaker: int = 0) -> Audio:
        """Convierte texto (una o varias frases) en audio mono."""

    def problems(self) -> list[str]:
        """Códigos de problemas del sistema que impiden usar el motor (p. ej. 'espeak_missing')."""
        return []
