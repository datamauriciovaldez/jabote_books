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
    py = re.search(r'^version = "(.+?)"', (ROOT / "pyproject.toml").read_text(), re.M).group(1)
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())["services"]["audiolibro"]["image"]
    assert py == app.__version__ and compose.endswith(f":{py}")
    assert f"## {py}" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")


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
                "docs/ADDING_A_VOICE_ENGINE.md", "docs/RELEASING.md", "docs/TROUBLESHOOTING.md", "docs/DECISIONS.md"}
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


def test_readme_is_bilingual_and_has_required_sections():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for needle in ("## Español", "## English", "docker compose up", "install.bat", "./install.sh", "Colab",
                   "¿Algo falló?", "Aviso legal", "Legal notice", "Estado de las pruebas"):
        assert needle in text, needle
