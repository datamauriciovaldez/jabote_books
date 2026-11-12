"""Diccionario de pronunciación: sustituciones de texto aplicadas antes de sintetizar."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    source: str          # lo que aparece en el libro (p. ej. "ONU", "Hermione")
    spoken: str          # cómo debe leerse (p. ej. "o-nu", "Jermaione")
    whole_word: bool = True
    case_sensitive: bool = True


def parse_rules(raw: list[dict]) -> list[Rule]:
    """Convierte la lista JSON del proyecto en reglas, ignorando entradas vacías."""
    rules = []
    for r in raw or []:
        src = str(r.get("source", "")).strip()
        if not src:
            continue
        rules.append(Rule(src, str(r.get("spoken", "")), bool(r.get("whole_word", True)),
                          bool(r.get("case_sensitive", True))))
    return rules


def apply_rules(text: str, rules: list[Rule]) -> str:
    """Aplica las reglas en orden (las más largas primero para evitar solapes)."""
    for r in sorted(rules, key=lambda x: -len(x.source)):
        pat = re.escape(r.source)
        if r.whole_word:
            pat = rf"(?<![\w]){pat}(?![\w])"
        text = re.sub(pat, lambda _m, s=r.spoken: s, text, flags=0 if r.case_sensitive else re.IGNORECASE)
    return text
