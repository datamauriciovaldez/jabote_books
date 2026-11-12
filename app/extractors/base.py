"""Modelo común de libro y despachador de extractores por formato."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.errors import UserError


@dataclass
class Chapter:
    title: str
    text: str
    included: bool = True


@dataclass
class Book:
    title: str
    author: str = ""
    language: str = ""
    chapters: list[Chapter] = field(default_factory=list)
    cover: bytes | None = None
    cover_mime: str = ""
    warnings: list[str] = field(default_factory=list)


SUPPORTED = (".txt", ".epub")  # se amplía en la Fase 2: .pdf .docx .md


def extract(path: Path) -> Book:
    """Extrae un libro del archivo según su extensión."""
    ext = path.suffix.lower()
    if ext == ".txt":
        from app.extractors.txt import extract_txt

        return extract_txt(path)
    if ext == ".epub":
        from app.extractors.epub import extract_epub

        return extract_epub(path)
    raise UserError("unsupported_format", ext=ext or "?", supported=", ".join(SUPPORTED))
