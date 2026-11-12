"""Genera app/tts/kokoro_voices.json desde el repositorio ONNX oficial de Kokoro en Hugging Face.

Uso (necesita internet, solo para mantenedores):
    python tools/audit_kokoro.py > app/tts/kokoro_voices.json

Se niega a generar el catálogo si la licencia publicada de los pesos no es Apache-2.0. Solo se incluyen
voces en español e inglés (los idiomas de la aplicación).
"""
from __future__ import annotations

import json
import sys
import urllib.request

REPO = "onnx-community/Kokoro-82M-v1.0-ONNX"
UPSTREAM = "hexgrad/Kokoro-82M"
# fp32: la variante int8 (92 MB) resultó MÁS lenta en CPU (ver docs/DECISIONS.md)
MODEL_FILE = "onnx/model.onnx"
PREFIXES = {"ef": ("es", "es", "f"), "em": ("es", "es", "m"),
            "af": ("en", "en_US", "f"), "am": ("en", "en_US", "m"),
            "bf": ("en", "en_GB", "f"), "bm": ("en", "en_GB", "m")}
ESPEAK = {"es": "es", "en_US": "en-us", "en_GB": "en-gb"}


def get(url: str):
    with urllib.request.urlopen(url, timeout=60) as r:  # noqa: S310
        return json.load(r)


def main() -> None:
    for repo in (REPO, UPSTREAM):
        lic = get(f"https://huggingface.co/api/models/{repo}").get("cardData", {}).get("license")
        if lic != "apache-2.0":
            sys.exit(f"Licencia inesperada en {repo}: {lic!r}. No se genera el catálogo.")
    tree = {x["path"]: x for x in get(f"https://huggingface.co/api/models/{REPO}/tree/main?recursive=true")}
    model = tree[MODEL_FILE]
    voices = []
    for path, item in sorted(tree.items()):
        if not path.startswith("voices/") or not path.endswith(".bin"):
            continue
        vid = path.split("/")[-1][:-4]
        if vid[:2] not in PREFIXES or "_" not in vid:
            continue
        lang, locale, gender = PREFIXES[vid[:2]]
        voices.append({"id": vid, "lang": lang, "locale": locale, "name": vid.split("_", 1)[1], "gender": gender,
                       "espeak": ESPEAK[locale], "path": path, "size_bytes": item["lfs"]["size"],
                       "sha256": item["lfs"]["oid"]})
    json.dump({"source": f"https://huggingface.co/{REPO}", "license": "Apache-2.0", "sample_rate": 24000,
               "model": {"path": MODEL_FILE, "size_bytes": model["lfs"]["size"], "sha256": model["lfs"]["oid"]},
               "voices": voices}, sys.stdout, ensure_ascii=False, indent=1)
    print(f"\n# {len(voices)} voces (es/en)", file=sys.stderr)


if __name__ == "__main__":
    main()
