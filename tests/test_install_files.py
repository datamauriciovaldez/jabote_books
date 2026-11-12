"""Comprobaciones estáticas de los archivos de instalación (no se puede ejecutar Docker ni Windows aquí)."""
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent


def test_install_sh_is_valid_and_complete():
    sh = ROOT / "install.sh"
    assert subprocess.run(["sh", "-n", str(sh)], capture_output=True).returncode == 0
    text = sh.read_text(encoding="utf-8")
    for needle in ("ffmpeg", "espeak-ng", "-m venv", "-m app", "--check", "python3.12", "tesseract"):
        assert needle in text, needle
    assert sh.stat().st_mode & 0o111, "install.sh debe ser ejecutable"
    assert "(3, 10)" in text and 'requires-python = ">=3.10"' in (ROOT / "pyproject.toml").read_text()


def test_install_bat_is_crlf_ascii_and_complete():
    raw = (ROOT / "install.bat").read_bytes()
    assert raw.isascii(), "cmd.exe puede fallar con caracteres no ASCII"
    assert b"\n" not in raw.replace(b"\r\n", b""), "install.bat debe usar saltos de línea CRLF"
    text = raw.decode("ascii")
    for needle in ("ffmpeg", "espeak-ng", "-m venv", "-m app", "--check", "py -%%V", "pause",
                   "winget install Gyan.FFmpeg"):
        assert needle in text, needle
    labels = set(re.findall(r"^:(\w+)", text, re.M))
    assert set(re.findall(r"goto :(\w+)", text)) <= labels | {"eof"}  # todos los saltos tienen destino


def test_dockerfile_is_safe_and_complete():
    d = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert re.search(r"^FROM python:3\.(1[0-9])-slim", d, re.M) and ":latest" not in d
    assert "USER audiolibro" in d and "HEALTHCHECK" in d and "VOLUME /data" in d
    assert all(p in d for p in ("ffmpeg", "espeak-ng", "tesseract-ocr", "tesseract-ocr-spa"))
    assert "AUDIOLIBRO_HOST=0.0.0.0" in d and 'CMD ["python", "-m", "app"]' in d


def test_compose_exposes_only_localhost_and_keeps_data():
    c = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    svc = c["services"]["audiolibro"]
    assert svc["ports"] == ["127.0.0.1:8000:8000"]           # nadie más de la red local puede entrar
    assert "audiolibro-data:/data" in svc["volumes"] and "audiolibro-data" in c["volumes"]
    assert svc["build"] == "."


def test_dockerignore_keeps_data_and_git_out_of_the_image():
    ignored = (ROOT / ".dockerignore").read_text().split()
    assert {"data", ".git", ".venv"} <= set(ignored)
