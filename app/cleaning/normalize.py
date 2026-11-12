"""Limpieza y normalización de texto para locución."""
from __future__ import annotations

import re
import unicodedata

_INVISIBLE = dict.fromkeys(map(ord, "­​‌‍⁠﻿"), None)
_SUPERSCRIPTS = "¹²³⁴⁵⁶⁷⁸⁹⁰"
_PAGE_NUM = re.compile(
    r"^\s*(?:[-–—]\s*)?(?:(?:p[áa]g(?:ina|e)?\.?|page)\s*)?\d{1,4}(?:\s*(?:/|de|of)\s*\d{1,4})?"
    r"(?:\s*[-–—])?\s*$",
    re.IGNORECASE,
)
_FOOTNOTE_MARK = re.compile(r"\[\d{1,3}\]|\[\*+\]|[" + _SUPERSCRIPTS + r"]+")
_TERMINAL = tuple(".!?…:;»”\"')]—-")


def basic_clean(text: str) -> str:
    """Caracteres raros, espacios y saltos de línea uniformes (sin tocar la estructura)."""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace(" ", " ")
    text = text.translate(_INVISIBLE)
    text = text.replace("\t", " ").replace("\f", "\n\n")
    text = re.sub(r"[ ]{2,}", " ", text)
    text = re.sub(r"[ ]+\n", "\n", text)
    return text


def remove_page_numbers(text: str) -> str:
    """Quita líneas que son solo un número de página ('12', '- 12 -', 'Página 12')."""
    return "\n".join(ln for ln in text.split("\n") if not _PAGE_NUM.match(ln))


def remove_footnotes(text: str) -> str:
    """Quita llamadas a nota ([1], ¹) y definiciones de notas al pie con formato [n]."""
    out = [ln for ln in text.split("\n") if not re.match(r"^\s*\[\d{1,3}\]\s+\S", ln)]
    return _FOOTNOTE_MARK.sub("", "\n".join(out))


def fix_hyphenation(text: str) -> str:
    """Une palabras partidas a final de línea: 'infor-\\nmación' -> 'información'."""
    # '-' y los guiones Unicode que usan los PDF (U+2010 hyphen, U+2011 non-breaking hyphen)
    return re.sub(r"(?<=[^\W\d_])[-\u2010\u2011][ ]*\n[ ]*(?=[a-záéíóúüñàèìòùç])", "", text)


def _ends_sentence(line: str) -> bool:
    return line.rstrip().endswith(_TERMINAL)


def split_paragraphs(text: str) -> list[str]:
    """Divide en párrafos. Desenvuelve líneas cortadas a mano si el texto está 'hard-wrapped'."""
    paragraphs: list[str] = []
    for block in re.split(r"\n\s*\n", text):
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        if len(lines) == 1:
            paragraphs.append(lines[0])
            continue
        unfinished = sum(1 for ln in lines[:-1] if not _ends_sentence(ln))
        if unfinished >= 0.5 * (len(lines) - 1):
            paragraphs.append(" ".join(lines))  # líneas cortadas por el ancho de página
        else:
            paragraphs.extend(lines)  # una línea = un párrafo (versos, diálogos)
    return paragraphs


def speech_ready(paragraph: str) -> str:
    """Ajustes finales para que el motor lea con naturalidad."""
    p = paragraph.strip()
    p = p.replace("…", "...")
    p = re.sub(r"\.{4,}", "...", p)
    p = re.sub(r"^[—–-]\s*", "", p)            # raya inicial de diálogo
    p = re.sub(r"\s*[—–]\s*", ", ", p)          # incisos con raya -> pausa
    p = re.sub(r",\s*,", ",", p)
    p = re.sub(r"\s+([,.;:!?])", r"\1", p)
    p = re.sub(r"[«»“”\"]", "", p)
    p = re.sub(r"\s{2,}", " ", p).strip(" ,")
    return p


def clean_chapter_text(raw: str) -> str:
    """Pipeline completo de limpieza; devuelve párrafos separados por línea en blanco."""
    t = basic_clean(raw)
    t = remove_page_numbers(t)
    t = remove_footnotes(t)
    t = fix_hyphenation(t)
    paras = [p for p in split_paragraphs(t) if re.search(r"\w", p)]
    return "\n\n".join(paras)


def paragraphs_for_speech(chapter_text: str) -> list[str]:
    """Párrafos listos para sintetizar (ya limpios, con raya de diálogo convertida en pausa)."""
    out = []
    for p in re.split(r"\n\s*\n", chapter_text):
        s = speech_ready(p)
        if s and re.search(r"\w", s):
            if not s.endswith((".", "!", "?", ":", ";", "…")):
                s += "."  # los títulos y líneas sueltas necesitan pausa final
            out.append(s)
    return out
