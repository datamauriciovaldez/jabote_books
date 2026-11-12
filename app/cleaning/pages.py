"""Limpieza específica de documentos paginados (PDF/OCR): cabeceras, pies y párrafos entre páginas."""
from __future__ import annotations

import re
from collections import Counter

from app.cleaning.chapters import is_heading_line

_TERMINAL = (".", "!", "?", "…", ":", '"', "”", "»", ")")
EDGE_LINES = 3          # cuántas líneas por arriba y por abajo se consideran "borde de página"
MIN_PAGES = 4           # con menos páginas no hay forma fiable de detectar repeticiones


_NUM_EDGE = re.compile(r"^\s*\d+\s|\s\d+\s*$|^\s*\d+\s*$")


def _norm(line: str) -> str:
    """Clave de comparación. Los dígitos solo se ignoran si están en un extremo ("12 Título", "Título 12"):
    es el patrón de un número de página; una frase del texto que solo difiere en un número no es cabecera."""
    key = re.sub(r"\s+", " ", line.strip().lower())
    return re.sub(r"\d+", "#", key) if _NUM_EDGE.search(line) else key


def remove_repeated(pages: list[list[str]]) -> list[list[str]]:
    """Quita encabezados y pies de página: líneas del borde que se repiten en ≥ 40 % de las páginas.

    Los números cambian de página en página, así que se comparan con los dígitos normalizados.
    """
    if len(pages) < MIN_PAGES:
        return pages
    counts: Counter[str] = Counter()
    for lines in pages:
        nonempty = [ln for ln in lines if ln.strip()]
        edge = nonempty[:EDGE_LINES] + nonempty[-EDGE_LINES:]
        counts.update({_norm(ln) for ln in edge})
    threshold = max(3, int(0.4 * len(pages)))
    repeated = {k for k, v in counts.items() if v >= threshold and k and len(k) <= 90}
    out = []
    for lines in pages:
        nonempty_idx = [i for i, ln in enumerate(lines) if ln.strip()]
        edge_idx = set(nonempty_idx[:EDGE_LINES] + nonempty_idx[-EDGE_LINES:])
        out.append([ln for i, ln in enumerate(lines) if not (i in edge_idx and _norm(ln) in repeated)])
    return out


def lines_to_paragraphs(lines: list[str]) -> str:
    """Reconstruye párrafos a partir de líneas de una página.

    Un párrafo termina tras una línea que acaba en puntuación y es notablemente más corta que el ancho
    habitual; los encabezados de capítulo se aíslan en su propio párrafo.
    """
    lines = [ln.strip() for ln in lines if ln.strip()]
    if not lines:
        return ""
    lengths = sorted(len(ln) for ln in lines)
    width = lengths[int(0.9 * (len(lengths) - 1))]
    out: list[str] = []
    for i, ln in enumerate(lines):
        heading = is_heading_line(ln)
        prev_heading = i > 0 and is_heading_line(lines[i - 1])
        if heading or prev_heading:
            out.append("\n\n" if out else "")
        out.append(ln)
        short_end = ln.endswith(_TERMINAL) and len(ln) < 0.7 * width
        out.append("\n\n" if short_end else "\n")
    return "".join(out).strip()


def join_pages(page_texts: list[str]) -> str:
    """Une páginas; si una frase continúa en la página siguiente, no se corta el párrafo."""
    out = ""
    for text in page_texts:
        text = text.strip()
        if not text:
            continue
        if not out:
            out = text
            continue
        last = out.rstrip().rsplit("\n", 1)[-1].strip()
        first = text.lstrip()[:1]
        cont = bool(last) and not last.endswith(_TERMINAL) and first.islower()
        out += ("\n" if cont else "\n\n") + text
    return out
