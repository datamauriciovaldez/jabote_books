"""Lanzador de escritorio: abre AudioLibro Libre en su propia ventana (o en el navegador como plan B).

Se usa como punto de entrada de la app empaquetada (`packaging/audiolibro.spec`) y también con
`python -m app.desktop`. Modos:

    (sin opciones)   ventana propia con pywebview; si no está disponible, abre el navegador
    --browser        abre el navegador (no usa pywebview)
    --no-open        solo arranca el servidor (pruebas y servidores)
    --self-test      comprueba ffmpeg, espeak-ng, el motor de voz y la interfaz, e imprime un informe
    --version        muestra la versión

La app empaquetada lleva dentro ffmpeg y espeak-ng (carpeta `bin/`); aquí se localizan y se ponen en el PATH.
Los datos (voces, proyectos, audio) van a la carpeta de datos del usuario, no dentro de la app.
"""
from __future__ import annotations

import argparse
import contextlib
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import webbrowser
from collections.abc import Callable, MutableMapping, Sequence
from pathlib import Path

from app import __version__

APP_NAME = "AudioLibro Libre"
DATA_FOLDER = "AudioLibroLibre"
PREFERRED_PORT = 8000


# --------------------------------------------------------------------------------- rutas y entorno
def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def user_data_dir(system: str | None = None, home: Path | None = None,
                  environ: MutableMapping[str, str] | None = None) -> Path:
    """Carpeta de datos del usuario según el sistema (macOS: ~/Library/Application Support/AudioLibroLibre)."""
    system = system or sys.platform
    home = home or Path.home()
    env = os.environ if environ is None else environ
    if system == "darwin":
        return home / "Library" / "Application Support" / DATA_FOLDER
    if system.startswith("win"):
        return Path(env.get("APPDATA") or home / "AppData" / "Roaming") / DATA_FOLDER
    return Path(env.get("XDG_DATA_HOME") or home / ".local" / "share") / "audiolibro-libre"


def bundle_roots() -> list[Path]:
    """Carpetas donde la app empaquetada puede guardar sus recursos (distintas según PyInstaller/macOS)."""
    roots: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(Path(meipass))
    exe = Path(sys.executable).resolve()
    roots += [exe.parent.parent / "Resources", exe.parent.parent / "Frameworks", exe.parent]
    return [r for i, r in enumerate(roots) if r not in roots[:i]]


def find_bundled_bin(roots: Sequence[Path] | None = None) -> Path | None:
    """Carpeta `bin/` con el ffmpeg incluido en la app, si existe."""
    for root in roots if roots is not None else bundle_roots():
        if (root / "bin" / "ffmpeg").is_file():
            return root / "bin"
    return None


def prepare_environment(environ: MutableMapping[str, str] | None = None,
                        roots: Sequence[Path] | None = None, force_data_dir: bool = False) -> dict[str, str]:
    """Deja listo el entorno: carpeta de datos, ffmpeg y espeak-ng incluidos. Devuelve lo que ha cambiado."""
    env = os.environ if environ is None else environ
    changed: dict[str, str] = {}
    if "AUDIOLIBRO_DATA" not in env and (is_frozen() or force_data_dir):
        changed["AUDIOLIBRO_DATA"] = str(user_data_dir())
    bin_dir = find_bundled_bin(roots)
    if bin_dir is not None:
        changed["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
        resources = bin_dir.parent
        if (resources / "espeak-ng-data").is_dir() and "ESPEAK_DATA_PATH" not in env:
            changed["ESPEAK_DATA_PATH"] = str(resources)
        if (bin_dir / "espeak-ng").is_file() and "AUDIOLIBRO_ESPEAK" not in env:
            changed["AUDIOLIBRO_ESPEAK"] = str(bin_dir / "espeak-ng")
    env.update(changed)
    return changed


# ------------------------------------------------------------------------------------------ servidor
def pick_free_port(preferred: int = PREFERRED_PORT, tries: int = 20) -> int:
    """Primer puerto libre desde `preferred` (así se pueden abrir dos copias sin chocar)."""
    for port in range(preferred, preferred + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:  # nadie escucha: está libre
                return port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class ServerThread:
    """Servidor de la app (uvicorn) en un hilo, con arranque y parada controlados."""

    def __init__(self, port: int) -> None:
        import uvicorn

        from app.web.main import app

        self.port = port
        self.server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
        self.thread = threading.Thread(target=self.server.run, name="audiolibro-server", daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/"

    def start(self, timeout: float = 30.0) -> bool:
        self.thread.start()
        end = time.monotonic() + timeout
        while time.monotonic() < end and self.thread.is_alive():
            with contextlib.suppress(OSError, ValueError):
                urllib.request.urlopen(self.url + "api/system", timeout=2)  # noqa: S310
                return True
            time.sleep(0.2)
        return False

    def stop(self, timeout: float = 8.0) -> None:
        self.server.should_exit = True
        self.thread.join(timeout)


def show_error(message: str) -> None:
    """Avisa al usuario: diálogo nativo en macOS (la app no tiene terminal) y consola en el resto."""
    print(f"[!] {message}", file=sys.stderr)
    if sys.platform == "darwin":
        safe = message.replace("\\", "\\\\").replace('"', "'")
        with contextlib.suppress(OSError):
            subprocess.run(["osascript", "-e", f'display dialog "{safe}" with title "{APP_NAME}" buttons {{"OK"}}'],
                           check=False, timeout=120)


# ----------------------------------------------------------------------------------------- autopruebas
Check = tuple[str, bool, str, bool]  # (nombre, correcto, detalle, obligatorio)


def _run(cmd: list[str], timeout: int = 60) -> str:
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    return (out.stdout + out.stderr).strip()


def _check_ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("ffmpeg no está en el PATH")
    banner = _run([exe, "-hide_banner", "-version"])
    config = next((ln for ln in banner.splitlines() if ln.startswith("configuration:")), "")
    bundled = find_bundled_bin()
    if bundled is not None and "--enable-gpl" in config:
        raise RuntimeError("el ffmpeg incluido es GPL; debe ser una compilación LGPL (ver docs/MAC_APP.md)")
    kind = "GPL" if "--enable-gpl" in config else "LGPL"
    return f"{banner.splitlines()[0]} · {kind} · {exe}"


def _check_ffmpeg_features() -> str:
    exe = shutil.which("ffmpeg") or "ffmpeg"
    wanted = {"-encoders": ("libmp3lame", " aac ", " flac "), "-muxers": (" mp4 ", " mp3 "),
              "-filters": ("loudnorm",), "-demuxers": (" concat ",)}
    missing = []
    for flag, needles in wanted.items():
        listing = _run([exe, "-hide_banner", flag])
        missing += [n.strip() for n in needles if n not in listing]
    if missing:
        raise RuntimeError("faltan en ffmpeg: " + ", ".join(missing))
    return "libmp3lame, aac, flac, mp4, mp3, loudnorm y concat disponibles"


def _check_ffmpeg_encode() -> str:
    """Repite lo que hace la exportación: normaliza, codifica MP3 y M4B con portada y marcadores."""
    from PIL import Image

    exe = shutil.which("ffmpeg") or "ffmpeg"
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        Image.new("RGB", (64, 64), (30, 90, 200)).save(work / "c.jpg")
        (work / "m.ffmeta").write_text(
            ";FFMETADATA1\ntitle=Prueba\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=0\nEND=1000\ntitle=Uno\n")
        base = [exe, "-hide_banner", "-loglevel", "error", "-y"]
        src = ["-f", "lavfi", "-i", "sine=frequency=220:duration=1"]
        steps = {
            "flac": base + src + ["-af", "loudnorm=I=-19:TP=-2.5:LRA=11", "-c:a", "flac", str(work / "a.flac")],
            "mp3": base + ["-i", str(work / "a.flac"), "-i", str(work / "c.jpg"), "-map", "0:a", "-map", "1:v",
                           "-c:v", "copy", "-c:a", "libmp3lame", "-b:a", "64k", "-id3v2_version", "3",
                           str(work / "a.mp3")],
            "m4b": base + ["-i", str(work / "a.flac"), "-i", str(work / "c.jpg"), "-i", str(work / "m.ffmeta"),
                           "-map", "0:a", "-map", "1:v", "-c:v", "copy", "-disposition:v:0", "attached_pic",
                           "-map_metadata", "2", "-map_chapters", "2", "-c:a", "aac", "-b:a", "64k",
                           "-movflags", "+faststart", "-f", "mp4", str(work / "a.m4b")],
        }
        for name, cmd in steps.items():
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
            if res.returncode != 0 or not Path(cmd[-1]).exists():
                raise RuntimeError(f"falló la codificación {name}: {res.stderr.strip()[-300:]}")
        # ffmpeg vuelca los marcadores como metadatos: así no hace falta ffprobe dentro de la app
        meta = _run([exe, "-hide_banner", "-i", str(work / "a.m4b"), "-f", "ffmetadata", "-"])
        if "[CHAPTER]" not in meta:
            raise RuntimeError("el M4B no tiene marcadores de capítulo")
    return "FLAC normalizado, MP3 con portada y M4B con capítulos y portada generados"


def _check_espeak() -> str:
    from app.tts.phonemize import espeak_binary, phonemize

    exe = espeak_binary()
    if not exe:
        raise RuntimeError("espeak-ng no encontrado")
    es, en = phonemize("hola mundo", "es"), phonemize("hello world", "en-us")
    if not es or not en:
        raise RuntimeError("espeak-ng no devuelve fonemas (¿falta su carpeta de datos?)")
    return f"{exe} · «hola mundo» → {es}"


def _check_onnx() -> str:
    import numpy
    import onnxruntime

    providers = ", ".join(onnxruntime.get_available_providers())
    return f"onnxruntime {onnxruntime.__version__}, numpy {numpy.__version__}, {providers}"


def _check_data_dir() -> str:
    from app.config import data_dir

    d = data_dir()
    probe = d / ".escritura"
    probe.write_text("ok")
    probe.unlink()
    return f"escritura correcta en {d}"


def _check_resources() -> str:
    from app.web import main as web_main

    # Rutas calculadas desde los módulos reales de la app (en el script de entrada empaquetado, `__file__`
    # de este archivo apunta a otra carpeta).
    app_dir = Path(web_main.__file__).resolve().parents[1]
    static = web_main.STATIC
    needed = [static / "index.html", static / "app.js", static / "i18n" / "es.json", static / "i18n" / "en.json",
              app_dir / "tts" / "voices.json", app_dir / "tts" / "kokoro_vocab.json",
              app_dir / "samples" / "quijote.txt", web_main.ROOT / "LICENSES.md"]
    missing = [str(p.name) for p in needed if not p.is_file()]
    if missing:
        raise RuntimeError("faltan recursos: " + ", ".join(missing))
    return "interfaz, traducciones, catálogos de voces, libros de ejemplo y licencias presentes"


def _check_window() -> str:
    import webview

    return f"pywebview {getattr(webview, '__version__', '?')}"


def run_checks() -> list[Check]:
    plan: list[tuple[str, Callable[[], str], bool]] = [
        ("Recursos de la app", _check_resources, True),
        ("Carpeta de datos", _check_data_dir, True),
        ("ffmpeg", _check_ffmpeg, True),
        ("ffmpeg: códecs y filtros", _check_ffmpeg_features, True),
        ("ffmpeg: exportación real", _check_ffmpeg_encode, True),
        ("espeak-ng", _check_espeak, True),
        ("Motor de voz (onnxruntime)", _check_onnx, True),
        ("Ventana propia (pywebview)", _check_window, False),
    ]
    results: list[Check] = []
    for name, fn, required in plan:
        try:
            results.append((name, True, fn(), required))
        except Exception as exc:  # noqa: BLE001 - el informe debe seguir aunque una comprobación falle
            results.append((name, False, f"{type(exc).__name__}: {exc}", required))
    return results


def self_test(stream=None) -> int:
    """Imprime un informe y devuelve 0 si todo lo obligatorio funciona."""
    out = stream or sys.stdout
    env_changes = prepare_environment(force_data_dir=False)
    print(f"{APP_NAME} {__version__} · autoprueba", file=out)
    print(f"Sistema: {platform.platform()} · {platform.machine()} · Python {platform.python_version()} · "
          f"{'empaquetada' if is_frozen() else 'desde el código'}", file=out)
    if env_changes:
        print("Entorno preparado:", ", ".join(sorted(env_changes)), file=out)
    results = run_checks()
    for name, ok, detail, required in results:
        mark = "OK " if ok else ("FALLO" if required else "aviso")
        print(f"  [{mark}] {name}: {detail}", file=out)
    failed = [r for r in results if not r[1] and r[3]]
    verdict = "todo correcto" if not failed else f"{len(failed)} comprobación(es) obligatoria(s) fallida(s)"
    print(f"\nRESULTADO: {verdict}", file=out)
    return 1 if failed else 0


# ----------------------------------------------------------------------------------------- arranque
def _open_window(url: str) -> bool:
    """Abre la ventana propia. Devuelve False si pywebview no está o falla (entonces se usa el navegador)."""
    try:
        import webview
    except ImportError:
        return False
    try:
        with contextlib.suppress(Exception):
            webview.settings["ALLOW_DOWNLOADS"] = True       # descargar el ZIP/M4B desde la ventana
        webview.create_window(APP_NAME, url, width=1180, height=860, min_size=(420, 600))
        webview.start()                                       # bloquea hasta que se cierra la ventana
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[!] No se pudo abrir la ventana propia ({exc}); se usa el navegador.", file=sys.stderr)
        return False


def run(mode: str = "window") -> int:
    prepare_environment(force_data_dir=is_frozen())
    server = ServerThread(pick_free_port())
    if not server.start():
        show_error("AudioLibro Libre no ha podido arrancar. Cierra otras copias de la aplicación e inténtalo "
                   "de nuevo.")
        return 1
    print(f"{APP_NAME} {__version__} listo en {server.url}", flush=True)
    try:
        if mode == "window" and _open_window(server.url):
            return 0                                          # ventana cerrada: se termina la app
        if mode != "no-open":
            webbrowser.open(server.url)
            print("Para cerrar, pulsa Ctrl+C (o cierra la aplicación desde el Dock).", flush=True)
        while server.thread.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="audiolibro", description=APP_NAME)
    parser.add_argument("--browser", action="store_true", help="abrir en el navegador en vez de en una ventana propia")
    parser.add_argument("--no-open", action="store_true", help="solo arrancar el servidor (sin ventana ni navegador)")
    parser.add_argument("--self-test", action="store_true", help="comprobar ffmpeg, espeak-ng y el motor de voz")
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args(argv)
    if args.version:
        print(f"{APP_NAME} {__version__}")
        return 0
    if args.self_test:
        return self_test()
    return run("no-open" if args.no_open else "browser" if args.browser else "window")


if __name__ == "__main__":
    sys.exit(main())
