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


def _run_espeak(text: str, voice: str) -> list[str]:
    exe = espeak_binary()
    if not exe:
        raise UserError("espeak_missing")
    proc = subprocess.run(
        [exe, "-q", "--ipa", "-v", voice, "--stdin"],
        input=text, capture_output=True, text=True, encoding="utf-8", check=False,
    )
    if proc.returncode != 0:
        raise UserError("espeak_failed", proc.stderr.strip()[:200])
    return [ln for ln in proc.stdout.split("\n") if ln.strip()]


def _ipa_clauses(clauses: list[str], voice: str) -> list[str]:
    """IPA de cada cláusula (sin puntuación), en el mismo orden.

    espeak-ng fusiona líneas consecutivas en una sola frase, así que se separan con una línea en
    blanco (un único proceso para todo el fragmento). Si el recuento no cuadra, se pregunta
    cláusula a cláusula: más lento pero siempre correcto.
    """
    if not clauses:
        return []
    out = _run_espeak("\n\n".join(clauses) + "\n", voice)
    if len(out) == len(clauses):
        return out
    return [" ".join(_run_espeak(c + "\n", voice)) for c in clauses]


@lru_cache(maxsize=4096)
def _phonemize_cached(text: str, voice: str) -> str:
    # Cláusulas separadas por la puntuación (se conserva: Piper la usa para pausas y entonación).
    parts = _CLAUSE.split(text)
    clauses = parts[0::2]
    puncts = [*parts[1::2], ""]
    speakable = [i for i, c in enumerate(clauses) if re.search(r"\w", c)]
    ipa = dict(zip(speakable, _ipa_clauses([clauses[i].strip() for i in speakable], voice), strict=True))
    pieces = []
    for i, punct in enumerate(puncts[: len(clauses)]):
        phon = _LANG_SWITCH.sub("", ipa.get(i, "")).strip()
        pieces.append(f"{phon}{punct}".strip())
    return " ".join(p for p in pieces if p)


def phonemize(text: str, voice: str) -> str:
    """Texto -> cadena IPA con la puntuación conservada. `voice` es el código de espeak ('es', 'en-us')."""
    return _phonemize_cached(text.strip(), voice)
