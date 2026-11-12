"""Extractor de Word (.docx) con python-docx (MIT). Los estilos 'Heading' definen los capítulos."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

from docx import Document
from docx.opc.exceptions import PackageNotFoundError

from app.cleaning.chapters import is_skippable_title
from app.cleaning.normalize import clean_chapter_text
from app.errors import UserError
from app.extractors.base import Book, Chapter
from app.extractors.txt import book_from_text


def extract_docx(path: Path) -> Book:
    try:
        doc = Document(str(path))
    except (PackageNotFoundError, zipfile.BadZipFile, KeyError, ValueError) as exc:
        raise UserError("docx_invalid", str(exc)[:200]) from exc

    props = doc.core_properties
    fallback = re.sub(r"[_]+", " ", path.stem).strip() or "Libro"
    title = (props.title or "").strip() or fallback
    author = (props.author or "").strip()

    chapters: list[tuple[str, list[str]]] = []
    intro: list[str] = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        style = (para.style.name if para.style is not None else "") or ""
        if re.match(r"(heading|t[ií]tulo)\s*[12]$", style, re.IGNORECASE):
            chapters.append((text, []))
        elif style.lower() in ("title", "título") and not chapters:
            title = text
        elif chapters:
            chapters[-1][1].append(text)
        else:
            intro.append(text)

    if not chapters:  # sin estilos de título: se detectan por el texto como en un .txt
        return _with_meta(book_from_text("\n\n".join(intro), title), title, author)

    result = []
    if len(" ".join(intro)) >= 200:
        result.append(Chapter("Inicio", clean_chapter_text("\n\n".join(intro))))
    for name, body in chapters:
        text = clean_chapter_text("\n\n".join(body))
        if text:
            result.append(Chapter(name, text, included=not is_skippable_title(name)))
    if not result:
        raise UserError("empty_book")
    return Book(title=title, author=author, chapters=result)


def _with_meta(book: Book, title: str, author: str) -> Book:
    book.title = title or book.title
    book.author = author or book.author
    return book
