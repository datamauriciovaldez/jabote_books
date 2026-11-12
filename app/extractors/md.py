"""Extractor de Markdown (.md): se quita la sintaxis y los '#' definen los capítulos."""
from __future__ import annotations

import re
from pathlib import Path

from app.extractors.base import Book
from app.extractors.txt import book_from_text, read_text


def strip_markdown(md: str) -> str:
    md = re.sub(r"```.*?```", "", md, flags=re.DOTALL)           # bloques de código
    md = re.sub(r"^---\n.*?\n---\n", "", md, flags=re.DOTALL)    # front-matter YAML
    md = re.sub(r"<!--.*?-->", "", md, flags=re.DOTALL)
    md = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)                 # imágenes
    md = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", md)             # enlaces -> texto
    md = re.sub(r"<[^>]+>", "", md)                              # HTML en línea
    md = re.sub(r"(\*\*|__)(.+?)\1", r"\2", md)                  # negrita
    md = re.sub(r"(?<![\w*])[*_](?=\S)(.+?)(?<=\S)[*_](?![\w*])", r"\1", md)  # cursiva
    md = re.sub(r"^\s{0,3}>\s?", "", md, flags=re.MULTILINE)     # citas
    md = re.sub(r"^\s*[-*+]\s+", "", md, flags=re.MULTILINE)     # viñetas
    md = re.sub(r"^\s*\d+[.)]\s+", "", md, flags=re.MULTILINE)   # listas numeradas
    md = re.sub(r"^\s*([-*_]\s*){3,}$", "", md, flags=re.MULTILINE)  # reglas horizontales
    return re.sub(r"`([^`]*)`", r"\1", md)


def extract_md(path: Path) -> Book:
    raw = read_text(path)
    h1 = re.findall(r"^#\s+(.+?)\s*#*$", raw, flags=re.MULTILINE)
    h2 = re.findall(r"^##\s+", raw, flags=re.MULTILINE)
    title = re.sub(r"[_]+", " ", path.stem).strip() or "Libro"
    if len(h1) == 1 and len(h2) >= 2:  # un solo '#' = título del libro; los '##' son capítulos
        title = h1[0]
        raw = re.sub(r"^#\s+.+$", "", raw, count=1, flags=re.MULTILINE)
    book = book_from_text(strip_markdown(raw), title)
    book.title = title if title else book.title
    return book
