"""División del texto en fragmentos (frases agrupadas) para sintetizar sin saturar la memoria."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.cleaning.normalize import paragraphs_for_speech
from app.cleaning.pronunciation import Rule, apply_rules
from app.cleaning.sentences import split_long, split_sentences

# Subir al cambiar cualquier cosa que altere el audio (fonemas, ids, motor): invalida la caché en disco.
CACHE_VERSION = "v2"
DEFAULT_MAX_CHARS = 300


@dataclass(frozen=True)
class Chunk:
    chapter: int      # id del capítulo
    index: int        # posición dentro del capítulo
    text: str         # texto exacto que se sintetiza (ya con pronunciación aplicada)
    para_end: bool    # ¿termina un párrafo? (se añade pausa de párrafo)
    key: str          # hash estable: mismo texto + misma voz/ajustes => mismo fichero

    @property
    def filename(self) -> str:
        return f"{self.index:05d}-{self.key}.flac"


def synthesis_signature(engine: str, voice: str, speaker: int, speed: float) -> str:
    return f"{CACHE_VERSION}|{engine}|{voice}|{speaker}|{speed:.3f}"


def _key(signature: str, text: str) -> str:
    return hashlib.sha256(f"{signature}\n{text}".encode()).hexdigest()[:16]


def chapter_chunks(chapter_id: int, title: str, text: str, *, signature: str, read_title: bool = True,
                   rules: list[Rule] | None = None, max_chars: int = DEFAULT_MAX_CHARS) -> list[Chunk]:
    """Fragmentos de un capítulo, en orden. Cada fragmento es una o varias frases (≤ max_chars)."""
    paragraphs = paragraphs_for_speech(text)
    if read_title and title.strip():
        paragraphs = paragraphs_for_speech(title.strip()) + paragraphs
    chunks: list[Chunk] = []
    for para in paragraphs:
        spoken = apply_rules(para, rules or [])
        sentences = [s for sent in split_sentences(spoken) for s in split_long(sent, max_chars)]
        groups: list[str] = []
        cur = ""
        for s in sentences:
            if cur and len(cur) + 1 + len(s) > max_chars:
                groups.append(cur)
                cur = s
            else:
                cur = f"{cur} {s}".strip()
        if cur:
            groups.append(cur)
        for i, g in enumerate(groups):
            chunks.append(Chunk(chapter_id, len(chunks), g, i == len(groups) - 1, _key(signature, g)))
    return chunks
