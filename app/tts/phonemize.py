"""Fonemización con espeak-ng, invocado como programa externo (es GPL-3: nunca se enlaza ni se copia)."""
from __future__ import annotations

import re
import shutil
import subprocess
from functools import lru_cache

from app.errors import UserError

_CLAUSE = re.compile(r"([,;:.!?…]+)")
_LANG_SWITCH = re.compile(r"\([a-z\-]{2,8}\)")


def espeak_binary() -> str | None:
    return shutil.which("espeak-ng") or shutil.which("espeak")


def _ipa_lines(lines: list[str], voice: str) -> list[str]:
    exe = espeak_binary()
    if not exe:
        raise UserError("espeak_missing")
    proc = subprocess.run(
        [exe, "-q", "--ipa", "-v", voice, "--stdin"],
        input="\n".join(lines) + "\n", capture_output=True, text=True, encoding="utf-8", check=False,
    )
    if proc.returncode != 0:
        raise UserError("espeak_failed", proc.stderr.strip()[:200])
    out = proc.stdout.split("\n")
    if out and out[-1] == "":
        out.pop()
    out += [""] * (len(lines) - len(out))  # por si espeak se come líneas vacías al final
    return out[: len(lines)]


@lru_cache(maxsize=4096)
def _phonemize_cached(text: str, voice: str) -> str:
    # Cláusulas separadas por la puntuación (se conserva: Piper la usa para la entonación).
    parts = _CLAUSE.split(text)
    clauses = [p for i, p in enumerate(parts) if i % 2 == 0]
    puncts = [p for i, p in enumerate(parts) if i % 2 == 1] + [""]
    todo = [c.strip() if re.search(r"\w", c) else "" for c in clauses]
    ipa = _ipa_lines([c if c else "." for c in todo], voice)
    pieces = []
    for c, phon, punct in zip(todo, ipa, puncts, strict=False):
        phon = _LANG_SWITCH.sub("", phon).strip() if c else ""
        pieces.append(f"{phon}{punct}".strip())
    return " ".join(p for p in pieces if p)


def phonemize(text: str, voice: str) -> str:
    """Texto -> cadena IPA con la puntuación conservada. `voice` es el código de espeak ('es', 'en-us')."""
    return _phonemize_cached(text.strip(), voice)
