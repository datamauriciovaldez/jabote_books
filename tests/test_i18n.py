import json
import re
from pathlib import Path

STATIC = Path(__file__).parent.parent / "app" / "web" / "static"


def load(lang):
    return json.loads((STATIC / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))


def test_same_keys_in_both_languages():
    es, en = load("es"), load("en")
    assert set(es) == set(en), (set(es) ^ set(en))


def test_placeholders_match():
    es, en = load("es"), load("en")
    ph = re.compile(r"\{(\w+)\}")
    for k in es:
        assert set(ph.findall(es[k])) == set(ph.findall(en[k])), k


def test_every_data_i18n_key_exists():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    keys = set(re.findall(r'data-i18n="([^"]+)"', html))
    for pair in re.findall(r'data-i18n-attr="([^"]+)"', html):
        keys |= {p.split("=")[1] for p in pair.split(";")}
    keys |= set(re.findall(r'\bt\("([a-z0-9_.]+)"', (STATIC / "app.js").read_text(encoding="utf-8")))
    es = load("es")
    assert not [k for k in keys if k not in es], [k for k in keys if k not in es]


def test_every_api_error_code_has_a_message():
    codes = set()
    for f in (Path(__file__).parent.parent / "app").rglob("*.py"):
        codes |= set(re.findall(r'(?:UserError|NotFound|Conflict)\(\s*"([a-z_]+)"', f.read_text(encoding="utf-8")))
    es = load("es")
    missing = [c for c in codes if f"errors.{c}.msg" not in es or f"errors.{c}.hint" not in es]
    assert not missing, missing
