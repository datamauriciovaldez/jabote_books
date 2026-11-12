"""Motor Piper: inferencia propia (MIT) con onnxruntime + espeak-ng externo.

No usa el paquete `piper-tts` (GPL-3 desde la 1.3). Ver docs/DECISIONS.md.
"""
from __future__ import annotations

import json
import os
import threading
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import onnxruntime as ort

from app.cleaning.sentences import split_long, split_sentences
from app.config import voices_dir
from app.errors import NotFound, UserError
from app.tts import catalog
from app.tts.base import Audio, ProgressCb, TTSEngine, VoiceInfo
from app.tts.download import download_file
from app.tts.phonemize import espeak_binary, phonemize

SENTENCE_GAP = 0.18      # segundos de silencio entre frases dentro de un fragmento
MAX_SENTENCE_CHARS = 260  # frases más largas se parten (Piper pierde calidad con entradas enormes)


@dataclass
class _Loaded:
    session: ort.InferenceSession
    id_map: dict[str, list[int]]
    sample_rate: int
    espeak_voice: str
    noise_scale: float
    length_scale: float
    noise_w: float
    has_sid: bool


class PiperEngine(TTSEngine):
    id = "piper"
    name = "Piper"

    def __init__(self) -> None:
        self._loaded: dict[str, _Loaded] = {}
        self._lock = threading.Lock()

    # ---------------------------------------------------------------- catálogo
    def _paths(self, voice_id: str) -> tuple[Path, Path]:
        catalog.get_raw(voice_id)
        d = voices_dir()
        return d / f"{voice_id}.onnx", d / f"{voice_id}.onnx.json"

    def is_installed(self, voice_id: str) -> bool:
        onnx, cfg = self._paths(voice_id)
        return onnx.exists() and cfg.exists()

    def list_voices(self, lang: str | None = None) -> list[VoiceInfo]:
        out = []
        for v in catalog.all_voices(self.id):
            if lang and v.lang != lang:
                continue
            out.append(VoiceInfo(**{**v.__dict__, "installed": self.is_installed(v.id)}))
        return out

    def problems(self) -> list[str]:
        return [] if espeak_binary() else ["espeak_missing"]

    def install(self, voice_id: str, progress: ProgressCb | None = None,
                cancel: threading.Event | None = None) -> None:
        onnx, cfg = self._paths(voice_id)
        raw = catalog.get_raw(voice_id)
        download_file(catalog.file_url(voice_id, ".onnx.json"), cfg, cancel=cancel)
        download_file(catalog.file_url(voice_id, ".onnx"), onnx, expected_size=raw["size_bytes"],
                      sha256=raw.get("sha256", ""), progress=progress, cancel=cancel)

    # ------------------------------------------------------------------ síntesis
    def _load(self, voice_id: str) -> _Loaded:
        with self._lock:
            if voice_id in self._loaded:
                return self._loaded[voice_id]
            if not self.is_installed(voice_id):
                raise NotFound("voice_not_installed", voice=voice_id)
            onnx, cfg_path = self._paths(voice_id)
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            if cfg.get("phoneme_type", "espeak") != "espeak":
                raise UserError("voice_unsupported", cfg.get("phoneme_type", "?"), voice=voice_id)
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = max(1, min(4, os.cpu_count() or 1))
            opts.log_severity_level = 3
            avail = ort.get_available_providers()
            providers = [p for p in ("CUDAExecutionProvider", "CPUExecutionProvider") if p in avail]
            session = ort.InferenceSession(str(onnx), opts, providers=providers or ["CPUExecutionProvider"])
            inf = cfg.get("inference", {})
            loaded = _Loaded(
                session=session, id_map=cfg["phoneme_id_map"], sample_rate=cfg["audio"]["sample_rate"],
                espeak_voice=cfg.get("espeak", {}).get("voice", "es"),
                noise_scale=inf.get("noise_scale", 0.667), length_scale=inf.get("length_scale", 1.0),
                noise_w=inf.get("noise_w", 0.8),
                has_sid="sid" in {i.name for i in session.get_inputs()},
            )
            self._loaded[voice_id] = loaded
            return loaded

    @staticmethod
    def _ids(phonemes: str, id_map: dict[str, list[int]]) -> list[int]:
        pad, bos, eos = id_map["_"], id_map["^"], id_map["$"]
        ids = [*bos, *pad]  # Piper: BOS, PAD, (fonema, PAD)…, EOS. Sin ese primer PAD se come el inicio.
        for ch in unicodedata.normalize("NFD", phonemes):
            if ch in id_map:
                ids.extend(id_map[ch])
                ids.extend(pad)
        ids.extend(eos)
        return ids

    def _infer(self, v: _Loaded, ids: list[int], speed: float, speaker: int) -> np.ndarray:
        feed = {
            "input": np.array([ids], dtype=np.int64),
            "input_lengths": np.array([len(ids)], dtype=np.int64),
            "scales": np.array([v.noise_scale, v.length_scale / max(0.25, speed), v.noise_w], dtype=np.float32),
        }
        if v.has_sid:
            feed["sid"] = np.array([speaker], dtype=np.int64)
        out = v.session.run(None, feed)[0]
        return np.asarray(out, dtype=np.float32).reshape(-1)

    def synthesize(self, text: str, voice_id: str, *, speed: float = 1.0, speaker: int = 0) -> Audio:
        v = self._load(voice_id)
        sentences = [s for sent in split_sentences(text) for s in split_long(sent, MAX_SENTENCE_CHARS)]
        gap = np.zeros(int(SENTENCE_GAP * v.sample_rate), dtype=np.float32)
        pieces: list[np.ndarray] = []
        for sent in sentences:
            ids = self._ids(phonemize(sent, v.espeak_voice), v.id_map)
            if len(ids) <= 3:  # sin fonemas pronunciables (solo símbolos)
                continue
            if pieces:
                pieces.append(gap)
            pieces.append(self._infer(v, ids, speed, speaker))
        if not pieces:
            return Audio(np.zeros(int(0.1 * v.sample_rate), dtype=np.float32), v.sample_rate)
        return Audio(np.clip(np.concatenate(pieces), -1.0, 1.0), v.sample_rate)
