"""Extractor de PDF con pypdf (BSD). PDFs escaneados: OCR opcional (ver ocr.py)."""
from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.cleaning.chapters import is_skippable_title, split_chapters
from app.cleaning.normalize import basic_clean, clean_chapter_text
from app.cleaning.pages import join_pages, lines_to_paragraphs, remove_repeated
from app.errors import UserError
from app.extractors import ocr
from app.extractors.base import Book, Chapter

Progress = Callable[[str, int, int], None]  # (etapa, hecho, total)
JUNK_TITLE = re.compile(r"(microsoft word|\.docx?|\.indd|untitled|sin t[ií]tulo|^\s*$)", re.IGNORECASE)
MIN_CHARS_PER_PAGE = 40     # por debajo, la página se considera imagen (escaneada)
SMALL_FONT = 0.85           # fuentes < 85 % de la dominante en el pie = notas al pie


def _page_lines(page) -> list[str]:
    """Líneas de la página (de arriba abajo) sin texto pequeño del pie (notas) ni superíndices sueltos."""
    segs: list[tuple[float, float, float, str]] = []

    def visit(text, cm, tm, _font, size):
        if text and text.strip("\n"):
            scale = abs(tm[3]) if tm[3] else 1.0
            segs.append((tm[5] * (cm[3] or 1) + cm[5], tm[4] * (cm[0] or 1) + cm[4], size * scale, text))

    try:
        plain = page.extract_text(visitor_text=visit)
    except (KeyError, ValueError, TypeError, AttributeError):
        return page.extract_text().split("\n")
    if not segs:
        return (plain or "").split("\n")
    sizes: Counter[float] = Counter()
    for _, _, size, text in segs:
        sizes[round(size, 1)] += len(text)
    body = max(sizes, key=lambda k: sizes[k])
    ys = [s[0] for s in segs]
    low, high = min(ys), max(ys)
    foot_limit = low + 0.25 * (high - low)
    kept = [s for s in segs
            if not (s[2] < SMALL_FONT * body and (s[0] <= foot_limit or re.fullmatch(r"[\d\s*†‡]+", s[3])))]
    lines: dict[float, list[tuple[float, str]]] = {}
    for y, x, _, text in kept:
        key = next((k for k in lines if abs(k - y) < 2.0), y)
        lines.setdefault(key, []).append((x, text.replace("\n", " ")))
    return ["".join(t for _, t in sorted(parts)).strip() for _, parts in sorted(lines.items(), reverse=True)]


def _meta_title(reader: PdfReader, fallback: str) -> tuple[str, str]:
    meta = reader.metadata
    title = (meta.title or "").strip() if meta else ""
    author = (meta.author or "").strip() if meta else ""
    return (fallback if JUNK_TITLE.search(title) else title), author


def _outline_chapters(reader: PdfReader, page_texts: list[str]) -> list[Chapter]:
    """Capítulos desde los marcadores del PDF (si el texto no tiene encabezados reconocibles)."""
    starts: list[tuple[int, str]] = []
    try:
        for item in reader.outline:
            if isinstance(item, list):
                continue  # solo primer nivel
            starts.append((reader.get_destination_page_number(item), str(item.title).strip()))
    except (PdfReadError, KeyError, ValueError, TypeError, AttributeError):
        return []
    starts = sorted({s for s in starts if s[0] is not None and s[0] >= 0})
    if len(starts) < 2:
        return []
    out = []
    for i, (page, title) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(page_texts)
        out.append(Chapter(title, join_pages(page_texts[page:max(end, page + 1)])))
    return out


def extract_pdf(path: Path, language: str = "es", progress: Progress | None = None) -> Book:
    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted and not reader.decrypt(""):
            raise UserError("pdf_encrypted")
        n = len(reader.pages)
    except UserError:
        raise
    except (PdfReadError, ValueError, OSError, KeyError) as exc:
        raise UserError("pdf_invalid", str(exc)[:200]) from exc
    if n == 0:
        raise UserError("empty_book")

    pages: list[list[str]] = []
    for i, page in enumerate(reader.pages):
        if progress:
            progress("read", i, n)
        pages.append(_page_lines(page))

    empty = [i for i, lines in enumerate(pages) if len("".join(lines).strip()) < MIN_CHARS_PER_PAGE]
    warnings: list[str] = []
    if len(empty) >= 0.5 * n:  # documento escaneado: texto solo desde imágenes
        recognised = ocr.ocr_pages(path, empty, language,
                                   (lambda d, t: progress("ocr", d, t)) if progress else None)
        for idx, text in recognised.items():
            pages[idx] = text.split("\n")
        warnings.append("ocr")

    pages = remove_repeated(pages)
    page_texts = [lines_to_paragraphs(p) for p in pages]
    title, author = _meta_title(reader, re.sub(r"[_]+", " ", path.stem).strip() or "Libro")
    full = basic_clean(join_pages(page_texts))
    chapters = split_chapters(full, fallback_title=title)
    if len(chapters) < 2:
        chapters = _outline_chapters(reader, page_texts) or chapters

    cleaned = []
    for ch in chapters:
        body = clean_chapter_text(ch.text)
        if body:
            cleaned.append(Chapter(ch.title, body, included=not is_skippable_title(ch.title)))
    if not cleaned:
        raise UserError("empty_book")
    return Book(title=title, author=author, language=language if "ocr" in warnings else "",
                chapters=cleaned, warnings=warnings)
