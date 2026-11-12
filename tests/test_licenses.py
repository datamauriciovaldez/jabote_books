import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
ALLOWED = ("CC0-1.0", "Public-Domain", "Unlicense", "MIT", "Apache-2.0", "CC-BY-3.0", "CC-BY-4.0")


def test_catalog_has_only_permissive_voices():
    for v in json.loads((ROOT / "app/tts/voices.json").read_text(encoding="utf-8"))["voices"]:
        assert v["license"] in ALLOWED, (v["id"], v["license"])
        assert v["sha256"] and v["size_bytes"] > 0


def test_licenses_md_is_up_to_date():
    out = subprocess.run([sys.executable, str(ROOT / "tools/gen_licenses.py")], capture_output=True,
                         text=True, check=True, encoding="utf-8").stdout
    assert out.strip() == (ROOT / "LICENSES.md").read_text(encoding="utf-8").strip(), \
        "LICENSES.md desactualizado: python tools/gen_licenses.py > LICENSES.md"


def test_no_ci_or_paid_dependencies():
    assert not (ROOT / ".github").exists()
    banned = ("ebooklib", "pymupdf", "fitz", "mutagen", "piper-tts", "kokoro-onnx", "phonemizer", "edge-tts",
              "TTS==", "openai", "elevenlabs")
    deps = (ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
    assert not [b for b in banned if b.lower() in deps]
