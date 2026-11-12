"""Coherencia del repositorio: versión única, notebook de Colab y contrato de los motores de voz."""
import ast
import json
import re
from pathlib import Path

import yaml

import app
from app.tts import available_engines, get_engine
from app.tts.base import TTSEngine, VoiceInfo

ROOT = Path(__file__).parent.parent


def test_version_is_the_same_everywhere():
    # (el CHANGELOG puede tener una sección "Sin publicar" por encima de la versión actual)
    py = re.search(r'^version = "(.+?)"', (ROOT / "pyproject.toml").read_text(), re.M).group(1)
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())["services"]["audiolibro"]["image"]
    assert py == app.__version__ and compose.endswith(f":{py}")
    assert f"## {py}" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    spec = (ROOT / "packaging/audiolibro.spec").read_text()
    assert "__version__" in spec                      # la .app toma la versión de app/


def test_colab_notebook_is_valid_and_safe():
    nb = json.loads((ROOT / "notebooks/AudioLibroLibre_Colab.ipynb").read_text(encoding="utf-8"))
    assert nb["nbformat"] == 4 and nb["cells"]
    text = json.dumps(nb)
    assert "api_key" not in text.lower() and "token" not in text.lower().replace("tokenize", "")
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            src = "".join(line for line in cell["source"] if not line.lstrip().startswith(("!", "%")))
            ast.parse(src)                                     # cada celda de código es Python válido
    md = " ".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "markdown")
    assert "servidor de Google" in md and "derechos" in md    # avisa de la limitación de privacidad y del copyright


def test_every_registered_engine_honours_the_contract():
    assert {"piper", "kokoro"} <= set(available_engines())
    for engine_id in available_engines():
        eng = get_engine(engine_id)
        assert isinstance(eng, TTSEngine) and eng.id == engine_id and eng.name
        voices = eng.list_voices()
        assert voices and all(isinstance(v, VoiceInfo) and v.engine == engine_id for v in voices)
        assert {v.lang for v in voices} >= {"es", "en"}
        assert all(v.license and v.size_bytes >= 0 for v in voices)
        assert eng.voice_info(voices[0].id).id == voices[0].id
        assert isinstance(eng.problems(), list)


def test_documentation_links_and_images_exist():
    """Todos los enlaces relativos (y las capturas) de los documentos apuntan a archivos reales."""
    docs = [ROOT / "README.md", ROOT / "CONTRIBUTING.md", *sorted((ROOT / "docs").glob("*.md"))]
    required = {"README.md", "CONTRIBUTING.md", "LICENSES.md", "CHANGELOG.md", "docs/ARCHITECTURE.md",
                "docs/ADDING_A_VOICE_ENGINE.md", "docs/RELEASING.md", "docs/TROUBLESHOOTING.md", "docs/DECISIONS.md",
                "docs/MAC_APP.md"}
    assert all((ROOT / r).is_file() for r in required)
    broken = []
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        targets = re.findall(r"\]\(([^)\s]+)\)", text) + re.findall(r'src="([^"]+)"', text)
        for t in targets:
            if t.startswith(("http", "#", "mailto:")):
                continue
            if not (doc.parent / t.split("#")[0]).exists():
                broken.append((doc.name, t))
    assert not broken, broken
    assert len(list((ROOT / "docs/img").glob("*.jpg"))) >= 6


BILINGUAL_DOCS = ["README.md", "CONTRIBUTING.md", "LICENSES.md", "CHANGELOG.md", "docs/ARCHITECTURE.md",
                  "docs/ADDING_A_VOICE_ENGINE.md", "docs/RELEASING.md", "docs/TROUBLESHOOTING.md", "docs/MAC_APP.md",
                  "packaging/THIRD_PARTY_NOTICES.md"]


def test_readme_is_bilingual_english_first_with_required_sections():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert text.index("## English") < text.index("## Español")           # inglés primero
    for needle in ("docker compose up", "install.bat", "./install.sh", "Colab", "Troubleshooting",
                   "Solución de problemas", "Legal notice", "Aviso legal", "Test status", "Estado de las pruebas",
                   "docs/img/en-1-upload.jpg", "docs/img/es-1-upload.jpg"):
        assert needle in text, needle
    for section in ("Installation", "Instalación", "Privacy and offline operation", "Privacidad y funcionamiento"):
        assert section in text, section
    # cada sección en inglés aparece antes que su equivalente en español
    assert text.index("### Installation") < text.index("### Instalación")
    assert text.index("### Troubleshooting") < text.index("### Solución de problemas")


def test_every_document_is_bilingual_with_english_first():
    for name in BILINGUAL_DOCS:
        text = (ROOT / name).read_text(encoding="utf-8")
        en, es = text.find('name="english"'), text.find('name="español"')
        if name in ("CHANGELOG.md",):
            en, es = text.find("**English**"), text.find("**Español**")
        assert 0 <= en < es, f"{name}: debe incluir inglés y después español"
    decisions = (ROOT / "docs/DECISIONS.md").read_text(encoding="utf-8")
    assert decisions.index('name="english-summary"') < decisions.index('name="registro-detallado-en-español"')


def test_documentation_uses_neutral_professional_language():
    """Sin referencias personales (la audiencia es "el usuario"/"the user") y sin emojis en la documentación."""
    import unicodedata
    files = [ROOT / n for n in BILINGUAL_DOCS] + [ROOT / "docs/DECISIONS.md"]
    for f in files:
        text = f.read_text(encoding="utf-8")
        for bad in ("amigo", "friend", "no técnic", "non-technical", "nontechnical"):
            assert bad not in text.lower(), f"{f.name}: contiene «{bad}»"
        emojis = {c for c in text if unicodedata.category(c) == "So" and ord(c) > 0x2000}
        assert not emojis, f"{f.name}: emojis {emojis}"
