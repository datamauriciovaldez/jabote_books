"""División en frases (es/en) respetando abreviaturas, decimales e iniciales."""
from __future__ import annotations

import re

_ABBR = {
    "sr", "sra", "srta", "dr", "dra", "prof", "lic", "ing", "av", "pág", "págs", "pag", "etc",
    "ud", "uds", "vd", "vds", "cap", "vol", "núm", "num", "art", "fig", "tel", "admón", "dpto",
    "mr", "mrs", "ms", "st", "jr", "vs", "no", "p", "pp", "ed", "eds", "cf", "ca", "fr",
    "gral", "excmo", "ilmo", "sta", "sto",
}
_SPLIT = re.compile(r"(?<=[.!?…])[\"”»')\]]*\s+(?=[\"“«¿¡(\[]*[A-ZÁÉÍÓÚÑÜ0-9])")


def split_sentences(paragraph: str) -> list[str]:
    """Devuelve las frases de un párrafo, sin perder texto."""
    parts = _SPLIT.split(paragraph.strip())
    out: list[str] = []
    for part in parts:
        if out:
            prev = out[-1]
            last = re.findall(r"([\wáéíóúñü]+)\.$", prev)
            initial = re.search(r"(?:^|\s)[A-ZÁÉÍÓÚÑ]\.$", prev)
            if (last and last[0].lower() in _ABBR) or initial:
                out[-1] = f"{prev} {part}"
                continue
        out.append(part)
    return [s.strip() for s in out if s.strip()]


def split_long(sentence: str, max_chars: int) -> list[str]:
    """Parte una frase demasiado larga por comas/punto y coma y, si hace falta, por palabras."""
    if len(sentence) <= max_chars:
        return [sentence]
    pieces = re.split(r"(?<=[,;:])\s+", sentence)
    out: list[str] = []
    cur = ""
    for piece in pieces:
        for sub in _hard_wrap(piece, max_chars):
            if cur and len(cur) + 1 + len(sub) > max_chars:
                out.append(cur)
                cur = sub
            else:
                cur = f"{cur} {sub}".strip()
    if cur:
        out.append(cur)
    return out


def _hard_wrap(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    words, out, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > max_chars:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        out.append(cur)
    return out
