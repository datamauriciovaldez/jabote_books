"""Detección automática de capítulos en texto plano."""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.extractors.base import Chapter

_ORD = (
    r"primero|primera|segundo|segunda|tercero|tercera|cuarto|cuarta|quinto|quinta|sexto|sexta|"
    r"s[eé]ptimo|s[eé]ptima|octavo|octava|noveno|novena|d[eé]cimo|d[eé]cima|und[eé]cimo|"
    r"duod[eé]cimo|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece|catorce|"
    r"quince|veinte|treinta|cuarenta|cincuenta|"
    r"first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|one|two|three|four|five|"
    r"six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|twenty|thirty"
)
_NUM = rf"(?:\d{{1,4}}|[IVXLCDM]{{1,8}}|{_ORD})"
# Palabras que identifican un capítulo solo si llevan número/ordinal detrás.
_NUMBERED = re.compile(
    rf"^(?:cap[ií]tulo|chapter|parte|part|libro|book|secci[oó]n|section|acto|act)\s+{_NUM}\b"
    r"[\s.:\-–—]*(.{0,100})$",
    re.IGNORECASE,
)
# Palabras que valen solas en su línea.
_STANDALONE = re.compile(
    r"^(?:pr[oó]logo|ep[ií]logo|prefacio|introducci[oó]n|conclusi[oó]n|conclusiones|"
    r"agradecimientos|dedicatoria|pref[aá]cio|preface|prologue|epilogue|introduction|"
    r"conclusion|acknowledg(?:e)?ments|dedication|afterword|foreword|appendix|ap[eé]ndice|"
    r"notas del autor|nota del autor|[ií]ndice|contenido|table of contents|contents)\.?$",
    re.IGNORECASE,
)
_ROMAN_ONLY = re.compile(r"^[IVXLCDM]{1,8}\.?$")
_NUM_ONLY = re.compile(r"^(\d{1,3})\.?$")
_MD_HEAD = re.compile(r"^#{1,3}\s+(.+?)\s*#*$")

_BOILER_START = re.compile(r"^\*{3}\s*START OF (?:THE|THIS) PROJECT GUTENBERG.*$", re.I | re.M)
_BOILER_END = re.compile(r"^\*{3}\s*END OF (?:THE|THIS) PROJECT GUTENBERG.*$", re.I | re.M)

# Capítulos que suelen no querer narrarse (se desmarcan por defecto).
SKIP_TITLES = re.compile(
    r"^(?:[ií]ndice|contenido|[ií]ndice general|table of contents|contents|copyright|"
    r"derechos|cr[eé]ditos|credits|licencia|license|colof[oó]n|portada|cover|title page|"
    r"p[aá]gina de t[ií]tulo|agradecimientos|acknowledg(?:e)?ments|sobre el autor|about the author|"
    r"bibliograf[ií]a|bibliography|notas|notes|[ií]ndice de|end of the project gutenberg)",
    re.IGNORECASE,
)


@dataclass
class _Head:
    line_no: int
    title: str
    kind: str  # keyword | roman | number | markdown


def strip_gutenberg(text: str) -> str:
    """Quita la cabecera y el pie legales de Project Gutenberg si están presentes."""
    start = _BOILER_START.search(text)
    if start:
        text = text[start.end():]
    end = _BOILER_END.search(text)
    if end:
        text = text[: end.start()]
    return text


def is_heading_line(line: str) -> bool:
    """¿Esta línea suelta parece un encabezado de capítulo ("Capítulo 3", "Prólogo"…)?"""
    line = line.strip()
    return len(line) <= 110 and bool(_NUMBERED.match(line) or _STANDALONE.match(line))


def is_skippable_title(title: str) -> bool:
    return bool(SKIP_TITLES.match(title.strip()))


def _find_heads(lines: list[str]) -> list[_Head]:
    heads: list[_Head] = []
    n = len(lines)
    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line or len(line) > 110:
            continue
        blank_before = i == 0 or not lines[i - 1].strip()
        blank_after = i == n - 1 or not lines[i + 1].strip()
        if (m := _MD_HEAD.match(line)):
            heads.append(_Head(i, m.group(1).strip(), "markdown"))
        elif not blank_before:
            continue
        elif _NUMBERED.match(line) or _STANDALONE.match(line):
            heads.append(_Head(i, line, "keyword"))
        elif blank_after and _ROMAN_ONLY.match(line):
            heads.append(_Head(i, line.rstrip("."), "roman"))
        elif blank_after and _NUM_ONLY.match(line):
            heads.append(_Head(i, line.rstrip("."), "number"))
    return _validate_numeric(heads)


def _validate_numeric(heads: list[_Head]) -> list[_Head]:
    """Los números sueltos solo cuentan si forman una secuencia 1,2,3… (si no, son nº de página)."""
    nums = [h for h in heads if h.kind == "number"]
    if nums:
        seq = [int(h.title) for h in nums]
        good = len(seq) >= 3 and seq[0] in (0, 1) and all(b - a == 1 for a, b in zip(seq, seq[1:], strict=False))
        if not good:
            heads = [h for h in heads if h.kind != "number"]
    romans = [h for h in heads if h.kind == "roman"]
    if romans and len(romans) < 2:  # una sola "I" suelta no basta
        heads = [h for h in heads if h.kind != "roman"]
    return heads


def split_chapters(text: str, fallback_title: str = "Texto") -> list[Chapter]:
    """Divide el texto en capítulos. Si no encuentra ninguno, devuelve uno solo."""
    lines = text.split("\n")
    heads = _find_heads(lines)
    if not heads:
        return [Chapter(fallback_title, text.strip())]

    chapters: list[Chapter] = []
    first = "\n".join(lines[: heads[0].line_no]).strip()
    if len(first) >= 200:
        chapters.append(Chapter("Inicio", first))
    for idx, h in enumerate(heads):
        end = heads[idx + 1].line_no if idx + 1 < len(heads) else len(lines)
        body_lines = lines[h.line_no + 1: end]
        title = h.title
        # subtítulo pegado al encabezado ("Capítulo I" / "Que trata de…")
        if (body_lines and body_lines[0].strip() and len(body_lines[0].strip()) < 120
                and not body_lines[0].rstrip().endswith((".", "!", "?", ","))
                and len(body_lines) > 1 and not body_lines[1].strip()):
            title = f"{title}. {body_lines[0].strip()}"
            body_lines = body_lines[1:]
        body = "\n".join(body_lines).strip()
        if len(body) < 40:  # entrada de índice o título sin contenido
            continue
        chapters.append(Chapter(re.sub(r"\s+", " ", title), body))
    return chapters or [Chapter(fallback_title, text.strip())]
