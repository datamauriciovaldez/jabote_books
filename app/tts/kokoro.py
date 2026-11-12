"""Motor Kokoro-82M (ONNX, Apache-2.0) con inferencia propia: onnxruntime + espeak-ng externo.

No usa los paquetes `kokoro-onnx` ni `phonemizer` (arrastran GPL-3). El flujo es el de su referencia:
texto -> fonemas IPA (espeak-ng) -> ids del vocabulario -> ONNX(input_ids, style, speed) -> audio a 24 kHz.
`style` es una fila de la matriz de la voz (510×256) elegida por el nº de tokens. Ver docs/DECISIONS.md.
"""
from __future__ import annotations

import json
import os
import re
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort

from app.cleaning.sentences import split_long, split_sentences
from app.config import HF_KOKORO_BASE, voices_dir
from app.errors import NotFound, UserError
from app.tts.base import Audio, ProgressCb, TTSEngine, VoiceInfo
from app.tts.download import download_file
from app.tts.phonemize import espeak_binary, phonemize

SAMPLE_RATE = 24000
MAX_TOKENS = 510            # límite del modelo
BATCH_TOKENS = 400          # se agrupan frases hasta este nº de tokens (Kokoro rinde mal con frases muy cortas)
MAX_SENTENCE_CHARS = 220
SENTENCE_GAP = 0.18
_PUNCT_ONLY = re.compile(r"^[\s.,;:!?…—\-\"'()«»“”]*$")
_DATA = Path(__file__).parent


@lru_cache(maxsize=1)
def _catalog() -> dict[str, Any]:
    return json.loads((_DATA / "kokoro_voices.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _vocab() -> dict[str, int]:
    return json.loads((_DATA / "kokoro_vocab.json").read_text(encoding="utf-8"))


def tokenize(phonemes: str) -> list[int]:
    """Cadena IPA -> ids. Los símbolos fuera del vocabulario se descartan (como en la referencia)."""
    vocab = _vocab()
    return [vocab[c] for c in phonemes if c in vocab][:MAX_TOKENS]


def style_for(voice: np.ndarray, n_tokens: int) -> np.ndarray:
    """Fila de estilo (1, 256) para una frase de `n_tokens` tokens."""
    return voice[min(max(n_tokens - 1, 0), voice.shape[0] - 1)]


class KokoroEngine(TTSEngine):
    id = "kokoro"
    name = "Kokoro"

    def __init__(self) -> None:
        self._session: ort.InferenceSession | None = None
        self._voices: dict[str, np.ndarray] = {}
        self._lock = threading.Lock()

    # ---------------------------------------------------------------- catálogo
    @staticmethod
    def _dir() -> Path:
        d = voices_dir() / "kokoro"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _model_path(self) -> Path:
        return self._dir() / "model.onnx"

    def _raw(self, voice_id: str) -> dict[str, Any]:
        for v in _catalog()["voices"]:
            if v["id"] == voice_id:
                return v
        raise NotFound("voice_unknown", voice=voice_id)

    def is_installed(self, voice_id: str) -> bool:
        self._raw(voice_id)
        return self._model_path().exists() and (self._dir() / f"{voice_id}.bin").exists()

    def list_voices(self, lang: str | None = None) -> list[VoiceInfo]:
        model_missing = not self._model_path().exists()
        model_size = _catalog()["model"]["size_bytes"] if model_missing else 0
        out = []
        for v in _catalog()["voices"]:
            if lang and v["lang"] != lang:
                continue
            have_voice = (self._dir() / f"{v['id']}.bin").exists()
            out.append(VoiceInfo(
                id=v["id"], engine=self.id, lang=v["lang"], locale=v["locale"], name=v["name"], quality="high",
                speakers=1, license="Apache-2.0", attribution_required=False, dataset_url=_catalog()["source"],
                # lo que hay que descargar AHORA: el modelo (una vez, compartido) + la voz
                size_bytes=model_size + (0 if have_voice else v["size_bytes"]),
                installed=not model_missing and have_voice))
        return out

    def problems(self) -> list[str]:
        return [] if espeak_binary() else ["espeak_missing"]

    def install(self, voice_id: str, progress: ProgressCb | None = None,
                cancel: threading.Event | None = None) -> None:
        raw = self._raw(voice_id)
        model, cat = self._model_path(), _catalog()["model"]
        todo = [(f"{HF_KOKORO_BASE}/{raw['path']}", self._dir() / f"{voice_id}.bin", raw["size_bytes"], raw["sha256"])]
        if not model.exists():
            todo.insert(0, (f"{HF_KOKORO_BASE}/{cat['path']}", model, cat["size_bytes"], cat["sha256"]))
        total, base = sum(t[2] for t in todo), 0
        for url, dest, size, sha in todo:
            if dest.exists():
                base += size
                continue
            offset = base

            def cb(done: int, _t: int, offset: int = offset) -> None:
                if progress:
                    progress(offset + done, total)

            download_file(url, dest, expected_size=size, sha256=sha, progress=cb, cancel=cancel)
            base += size

    # ------------------------------------------------------------------ síntesis
    def _load(self, voice_id: str) -> tuple[ort.InferenceSession, np.ndarray]:
        with self._lock:
            if not self.is_installed(voice_id):
                raise NotFound("voice_not_installed", voice=voice_id)
            if self._session is None:
                opts = ort.SessionOptions()
                opts.intra_op_num_threads = max(1, min(4, os.cpu_count() or 1))
                opts.log_severity_level = 3
                avail = ort.get_available_providers()
                providers = [p for p in ("CUDAExecutionProvider", "CPUExecutionProvider") if p in avail]
                self._session = ort.InferenceSession(str(self._model_path()), opts,
                                                     providers=providers or ["CPUExecutionProvider"])
            if voice_id not in self._voices:
                data = np.fromfile(self._dir() / f"{voice_id}.bin", dtype=np.float32)
                if data.size % 256:
                    raise UserError("voice_unsupported", "archivo de voz dañado", voice=voice_id)
                self._voices[voice_id] = data.reshape(-1, 1, 256)
            return self._session, self._voices[voice_id]

    @staticmethod
    def _batches(text: str, espeak_voice: str) -> list[str]:
        """Fonemas de `text` agrupados en lotes de ≤ BATCH_TOKENS tokens."""
        batches: list[str] = []
        cur = ""
        for piece in (p for sent in split_sentences(text) for p in split_long(sent, MAX_SENTENCE_CHARS)):
            ph = phonemize(piece, espeak_voice)
            if cur and len(tokenize(f"{cur} {ph}")) >= BATCH_TOKENS:
                batches.append(cur)
                cur = ph
            else:
                cur = f"{cur} {ph}".strip()
        if cur:
            batches.append(cur)
        return batches

    def synthesize(self, text: str, voice_id: str, *, speed: float = 1.0, speaker: int = 0) -> Audio:
        session, voice = self._load(voice_id)
        espeak_voice = self._raw(voice_id)["espeak"]
        gap = np.zeros(int(SENTENCE_GAP * SAMPLE_RATE), dtype=np.float32)
        pieces: list[np.ndarray] = []
        for ph in self._batches(text, espeak_voice):
            tokens = tokenize(ph)
            if len(tokens) < 2 or _PUNCT_ONLY.match(ph):  # nada pronunciable (solo signos): no se sintetiza
                continue
            feed = {"input_ids": np.array([[0, *tokens, 0]], dtype=np.int64),
                    "style": style_for(voice, len(tokens)),
                    "speed": np.array([max(0.25, speed)], dtype=np.float32)}
            out = np.asarray(session.run(None, feed)[0], dtype=np.float32).reshape(-1)
            if pieces:
                pieces.append(gap)
            pieces.append(out)
        if not pieces:
            return Audio(np.zeros(int(0.1 * SAMPLE_RATE), dtype=np.float32), SAMPLE_RATE)
        return Audio(np.clip(np.concatenate(pieces), -1.0, 1.0), SAMPLE_RATE)
