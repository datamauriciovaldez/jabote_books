"""Pruebas de los scripts de la app de macOS. No se pueden ejecutar en Linux (compilan para Apple Silicon),
así que se prueba lo que sí es verificable: sintaxis, que no entre nada GPL en ffmpeg y la verificación de hashes."""
import ast
import hashlib
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
MAC = ROOT / "tools" / "mac"
SCRIPTS = ["lib.sh", "build_ffmpeg.sh", "build_espeak.sh", "build_app.sh"]


@pytest.mark.parametrize("name", SCRIPTS)
def test_scripts_have_valid_bash_syntax(name):
    assert subprocess.run(["bash", "-n", str(MAC / name)], capture_output=True).returncode == 0
    if name != "lib.sh":
        assert (MAC / name).stat().st_mode & 0o111, f"{name} debe ser ejecutable"


def test_ffmpeg_is_built_lgpl_only():
    text = (MAC / "build_ffmpeg.sh").read_text(encoding="utf-8")
    flags = text[text.index("CONFIG_FLAGS="):text.index("( cd", text.index("CONFIG_FLAGS="))]
    assert "--disable-gpl" in flags and "--disable-nonfree" in flags and "--enable-libmp3lame" in flags
    for banned in ("--enable-gpl", "--enable-nonfree", "libx264", "libx265", "libfdk", "--enable-version3"):
        assert banned not in flags, banned
    assert "--enable-gpl" in text  # la comprobación posterior sí busca esa cadena para rechazar un ffmpeg GPL
    assert "assert_self_contained" in text and "loudnorm" in text


def test_app_build_signs_tests_and_ships_licenses_and_sources():
    text = (MAC / "build_app.sh").read_text(encoding="utf-8")
    for needle in ("codesign --force --deep --sign -", "--self-test", "hdiutil create", "THIRD_PARTY_NOTICES.md",
                   "dist/mac", "sources", "arm64", "Abrir igualmente"):
        assert needle in text, needle
    assert re.search(r"selftest.*RESULTADO: todo correcto|RESULTADO: todo correcto.*selftest", text, re.S)


def test_source_hashes_are_pinned_or_explicitly_unpinned():
    rows = [ln.split() for ln in (ROOT / "packaging/source-hashes.txt").read_text().splitlines()
            if ln.strip() and not ln.startswith("#")]
    assert {r[0] for r in rows} == {"lame", "ffmpeg", "espeak-ng"}
    for name, version, sha, url in rows:
        assert url.startswith("https://") and version in url
        assert sha == "UNPINNED" or re.fullmatch(r"[0-9a-f]{64}", sha), (name, sha)
    lame = next(r for r in rows if r[0] == "lame")
    assert lame[2] == "ddfe36cab873794038ae2c1210557ad34857a4b6bdc515785d1da9e175b1da1e"  # verificado


def test_pyinstaller_spec_is_valid_python_and_bundles_what_the_app_needs():
    spec = (ROOT / "packaging/audiolibro.spec").read_text(encoding="utf-8")
    ast.parse(spec)
    for needle in ("app/web/static", "voices.json", "kokoro_vocab.json", "app/samples", "LICENSES.md",
                   "collect_submodules(\"app\")", "BUNDLE", "org.audiolibrolibre.app", "desktop.py"):
        assert needle in spec, needle
    assert (ROOT / "packaging/icon-1024.png").is_file()


def test_notices_cover_every_redistributed_component():
    text = (ROOT / "packaging/THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    for needle in ("ffmpeg", "LGPL", "LAME", "espeak-ng", "GPL-3.0", "PyInstaller", "pywebview", "código fuente"):
        assert needle in text, needle


# ---- verificación de hashes de lib.sh (se prueba con tarballs locales file://)
def run_fetch(tmp_path, sha, trust=False, content=b"contenido de prueba"):
    tarball = tmp_path / "origen" / "demo-1.0.tar.gz"
    tarball.parent.mkdir(exist_ok=True)
    import io
    import tarfile
    with tarfile.open(tarball, "w:gz") as t:
        info = tarfile.TarInfo("demo-1.0/README")
        info.size = len(content)
        t.addfile(info, io.BytesIO(content))
    real = hashlib.sha256(tarball.read_bytes()).hexdigest()
    hashes = tmp_path / "hashes.txt"
    hashes.write_text(f"demo 1.0 {sha.replace('REAL', real)} file://{tarball}\n")
    script = f'''set -e
export HASHES="{hashes}"
source "{MAC / 'lib.sh'}"
SRC="{tmp_path / 'src'}"; mkdir -p "$SRC"
fetch_source demo
unpack "$TARBALL" "{tmp_path / 'out'}"
cat "$SRCDIR/README"'''
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(tmp_path)}
    if trust:
        env["AUDIOLIBRO_TRUST_NEW_SOURCES"] = "1"
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env, cwd=tmp_path)


def test_correct_hash_downloads_verifies_and_unpacks(tmp_path):
    res = run_fetch(tmp_path, "REAL")
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip().endswith("contenido de prueba")


def test_wrong_hash_is_rejected_and_download_deleted(tmp_path):
    res = run_fetch(tmp_path, "0" * 64)
    assert res.returncode != 0 and "no coincide" in res.stderr
    assert not (tmp_path / "src" / "demo-1.0.tar.gz").exists()


def test_unpinned_source_stops_unless_explicitly_trusted(tmp_path):
    blocked = run_fetch(tmp_path, "UNPINNED")
    assert blocked.returncode != 0 and "AUDIOLIBRO_TRUST_NEW_SOURCES=1" in blocked.stderr
    assert re.search(r"[0-9a-f]{64}", blocked.stdout + blocked.stderr)          # muestra el hash calculado
    ok = run_fetch(tmp_path, "UNPINNED", trust=True)
    assert ok.returncode == 0, ok.stderr


def test_real_lame_tarball_hash_matches_if_downloaded():
    """Si hay red, comprueba que la fuente de LAME fijada en el repositorio sigue coincidiendo."""
    import urllib.error
    import urllib.request
    url = "https://downloads.sourceforge.net/project/lame/lame/3.100/lame-3.100.tar.gz"
    try:
        data = urllib.request.urlopen(url, timeout=30).read()  # noqa: S310
    except (urllib.error.URLError, OSError):
        pytest.skip("sin red")
    assert hashlib.sha256(data).hexdigest() == "ddfe36cab873794038ae2c1210557ad34857a4b6bdc515785d1da9e175b1da1e"
