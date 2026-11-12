"""Audita las voces de rhasspy/piper-voices y genera el catálogo con licencia permisiva.

Uso (necesita internet, solo para mantenedores):
    python tools/audit_voices.py > app/tts/voices.json

Solo entran voces cuyo dataset tenga licencia CC0, dominio público, CC-BY,
Apache-2.0 o MIT. Se descartan CC-BY-SA, no comercial y desconocidas.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request

REPO = "rhasspy/piper-voices"
LANGS = ("es", "en")
BASE = f"https://huggingface.co/{REPO}"


def _get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as r:  # noqa: S310
        return r.read()


def classify(text: str) -> tuple[str, bool] | None:
    """Devuelve (etiqueta SPDX-like, requiere_atribucion) o None si no es permisiva."""
    t = text.lower()
    if re.search(r"\b(nc|noncommercial|non-commercial)\b|by-nc|sharealike|by-sa|share-alike|share alike", t):
        return None
    if "cc0" in t or "creativecommons.org/publicdomain/zero" in t:
        return "CC0-1.0", False
    if "unlicense.org" in t:
        return "Unlicense", False
    if "public domain" in t or "publicdomain" in t:
        return "Public-Domain", False
    if "apache" in t:
        return "Apache-2.0", True
    if re.search(r"\bmit\b", t):
        return "MIT", True
    m = re.search(r"(creativecommons\.org/licenses/by/([\d.]+)|cc[ -]by[ -]?([\d.]+))", t)
    if m or t.strip().endswith("attribution 4.0 international") or "cc by 4.0" in t:
        ver = (m.group(2) or m.group(3)) if m else "4.0"
        return f"CC-BY-{ver or '4.0'}", True
    return None


def main() -> None:
    entries, rejected = [], []
    for lang in LANGS:
        api = f"https://huggingface.co/api/models/{REPO}/tree/main/{lang}?recursive=true"
        tree = json.loads(_get(api))
        cards = [x["path"] for x in tree if x["path"].endswith("MODEL_CARD")]
        sizes = {x["path"]: x.get("lfs", {}).get("size", x.get("size", 0)) for x in tree}
        for card in sorted(cards):
            folder = card.rsplit("/", 1)[0]
            try:
                _, locale, name, quality = folder.split("/")
            except ValueError:
                continue
            text = _get(f"{BASE}/raw/main/{card}").decode("utf-8", "replace")
            m = re.search(r"\* License:\s*(.+)", text)
            lic_raw = m.group(1).strip() if m else ""
            url = (re.search(r"\* URL:\s*(.+)", text) or [None, ""])[1].strip()
            spk = int((re.search(r"\* Speakers:\s*(\d+)", text) or [None, "1"])[1])
            ok = classify(lic_raw)
            ident = f"{locale}-{name}-{quality}"
            if ok is None:
                rejected.append((ident, lic_raw))
                continue
            entries.append({
                "id": ident, "lang": lang, "locale": locale, "name": name, "quality": quality,
                "speakers": spk, "license": ok[0], "attribution_required": ok[1],
                "license_text": lic_raw, "dataset_url": url,
                "path": f"{folder}/{ident}", "size_bytes": sizes.get(f"{folder}/{ident}.onnx", 0),
            })
    json.dump({"source": BASE, "voices": entries}, sys.stdout, ensure_ascii=False, indent=1)
    print(f"\n# aceptadas={len(entries)} rechazadas={len(rejected)}", file=sys.stderr)
    for r in rejected:
        print("  rechazada:", r, file=sys.stderr)


if __name__ == "__main__":
    main()
