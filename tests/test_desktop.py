import io
import shutil
import socket
import urllib.request
from pathlib import Path

import pytest

from app import desktop
from app.tts.phonemize import espeak_binary

needs_tools = pytest.mark.skipif(not (shutil.which("ffmpeg") and espeak_binary()), reason="faltan ffmpeg/espeak-ng")


def test_user_data_dir_per_platform(tmp_path):
    home = tmp_path
    assert desktop.user_data_dir("darwin", home, {}) == home / "Library/Application Support/AudioLibroLibre"
    assert desktop.user_data_dir("win32", home, {"APPDATA": r"C:\Users\x\AppData\Roaming"}).name == "AudioLibroLibre"
    assert desktop.user_data_dir("linux", home, {}) == home / ".local/share/audiolibro-libre"
    assert desktop.user_data_dir("linux", home, {"XDG_DATA_HOME": "/x"}) == Path("/x/audiolibro-libre")


def make_bundle(root, with_espeak=True):
    (root / "bin").mkdir(parents=True)
    (root / "bin" / "ffmpeg").write_text("#!/bin/sh\n")
    if with_espeak:
        (root / "bin" / "espeak-ng").write_text("#!/bin/sh\n")
        (root / "espeak-ng-data").mkdir()
    return root


def test_bundled_tools_are_found_and_put_on_path(tmp_path):
    res = make_bundle(tmp_path / "Resources")
    env = {"PATH": "/usr/bin"}
    changed = desktop.prepare_environment(env, roots=[tmp_path / "nada", res])
    assert env["PATH"].startswith(str(res / "bin") + ":") or env["PATH"].startswith(str(res / "bin"))
    assert env["ESPEAK_DATA_PATH"] == str(res) and env["AUDIOLIBRO_ESPEAK"] == str(res / "bin" / "espeak-ng")
    assert "AUDIOLIBRO_DATA" not in changed       # fuera de la app empaquetada no se toca la carpeta de datos


def test_data_dir_is_set_for_the_packaged_app_but_never_overridden(tmp_path, monkeypatch):
    monkeypatch.setattr(desktop, "is_frozen", lambda: True)
    env = {}
    desktop.prepare_environment(env, roots=[])
    assert env["AUDIOLIBRO_DATA"] == str(desktop.user_data_dir())
    env2 = {"AUDIOLIBRO_DATA": "/mis/datos"}
    desktop.prepare_environment(env2, roots=[])
    assert env2["AUDIOLIBRO_DATA"] == "/mis/datos"   # lo que el usuario fija manda


def test_bundle_without_ffmpeg_is_ignored(tmp_path):
    (tmp_path / "bin").mkdir()
    assert desktop.find_bundled_bin([tmp_path]) is None


def test_pick_free_port_skips_busy_ports():
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        port = busy.getsockname()[1]
        assert desktop.pick_free_port(port, tries=3) != port


def test_server_starts_serves_and_stops():
    server = desktop.ServerThread(desktop.pick_free_port(8300))
    assert server.start(timeout=30)
    try:
        assert b"AudioLibro" in urllib.request.urlopen(server.url, timeout=5).read()
        assert urllib.request.urlopen(server.url + "api/system", timeout=5).status == 200
    finally:
        server.stop()
    assert not server.thread.is_alive()


@needs_tools
def test_self_test_passes_with_the_tools_installed():
    out = io.StringIO()
    code = desktop.self_test(out)
    text = out.getvalue()
    assert code == 0, text
    for needle in ("ffmpeg: exportación real", "espeak-ng", "Motor de voz", "RESULTADO: todo correcto"):
        assert needle in text, text
    assert "[FALLO]" not in text


def test_self_test_reports_missing_ffmpeg_with_nonzero_exit(monkeypatch):
    monkeypatch.setenv("PATH", "/nonexistent")
    out = io.StringIO()
    assert desktop.self_test(out) == 1
    text = out.getvalue()
    assert "[FALLO] ffmpeg" in text and "obligatoria(s) fallida(s)" in text


def test_missing_webview_falls_back_to_browser(monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, "webview", None)        # hace fallar `import webview`
    assert desktop._open_window("http://127.0.0.1:1/") is False


def test_cli_version_and_unknown_flags(capsys):
    assert desktop.main(["--version"]) == 0
    assert desktop.__version__ in capsys.readouterr().out
    with pytest.raises(SystemExit):
        desktop.main(["--no-existe"])
