"""Extractor de texto plano (.txt)."""
from __future__ import annotations

import re
from pathlib import Path

from app.cleaning.chapters import is_skippable_title, split_chapters, strip_gutenberg
from app.cleaning.normalize import basic_clean, clean_chapter_text
from app.errors import UserError
from app.extractors.base import Book, Chapter


def read_text(path: Path) -> str:
    """Lee un archivo probando codificaciones habituales."""
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise UserError("unreadable_text")  # pragma: no cover (latin-1 siempre decodifica)


def _gutenberg_meta(text: str) -> dict[str, str]:
    head = text[:4000]
    meta = {}
    for key in ("Title", "Author", "Language"):
        m = re.search(rf"^{key}:\s*(.+)$", head, re.MULTILINE)
        if m:
            meta[key.lower()] = m.group(1).strip()
    return meta


def book_from_text(text: str, fallback_title: str) -> Book:
    """Construye un Book desde texto ya leído (lo comparten txt, md y docx)."""
    text = basic_clean(text)
    meta = _gutenberg_meta(text)
    text = strip_gutenberg(text)
    chapters: list[Chapter] = []
    for ch in split_chapters(text, fallback_title=meta.get("title", fallback_title)):
        body = clean_chapter_text(ch.text)
        if body:
            chapters.append(Chapter(ch.title, body, included=not is_skippable_title(ch.title)))
    if not chapters:
        raise UserError("empty_book")
    lang = {"spanish": "es", "english": "en"}.get(meta.get("language", "").lower(), "")
    return Book(title=meta.get("title", fallback_title), author=meta.get("author", ""),
                language=lang, chapters=chapters)


def extract_txt(path: Path) -> Book:
    title = re.sub(r"[_]+", " ", path.stem).strip() or "Libro"
    return book_from_text(read_text(path), title)
