"""Modelo común de libro y despachador de extractores por formato."""
from __future__ import annotations

from collections.abc import Callable
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


SUPPORTED = (".txt", ".epub", ".pdf", ".docx", ".md")
Progress = Callable[[str, int, int], None]  # (etapa, hecho, total): "read" | "ocr"


def extract(path: Path, language: str = "es", progress: Progress | None = None) -> Book:
    """Extrae un libro del archivo según su extensión. `language` solo importa para el OCR."""
    ext = path.suffix.lower()
    if ext == ".txt":
        from app.extractors.txt import extract_txt

        return extract_txt(path)
    if ext == ".epub":
        from app.extractors.epub import extract_epub

        return extract_epub(path)
    if ext == ".pdf":
        from app.extractors.pdf import extract_pdf

        return extract_pdf(path, language or "es", progress)
    if ext == ".docx":
        from app.extractors.docx import extract_docx

        return extract_docx(path)
    if ext == ".md":
        from app.extractors.md import extract_md

        return extract_md(path)
    raise UserError("unsupported_format", ext=ext or "?", supported=", ".join(SUPPORTED))
