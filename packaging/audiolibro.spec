# -*- mode: python ; coding: utf-8 -*-
# Receta de PyInstaller de AudioLibro Libre. La misma sirve para Linux (pruebas) y macOS (.app).
#   pyinstaller --noconfirm packaging/audiolibro.spec
# En macOS, tools/mac/build_app.sh la ejecuta y luego copia ffmpeg y espeak-ng dentro de la .app.
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

ROOT = Path(SPECPATH).resolve().parent  # noqa: F821  (SPECPATH lo define PyInstaller)
sys.path.insert(0, str(ROOT))
from app import __version__  # noqa: E402

datas = [
    (str(ROOT / "app" / "web" / "static"), "app/web/static"),
    (str(ROOT / "app" / "tts" / "voices.json"), "app/tts"),
    (str(ROOT / "app" / "tts" / "kokoro_voices.json"), "app/tts"),
    (str(ROOT / "app" / "tts" / "kokoro_vocab.json"), "app/tts"),
    (str(ROOT / "app" / "samples"), "app/samples"),
    (str(ROOT / "LICENSES.md"), "."),
    (str(ROOT / "LICENSE"), "."),
]
binaries = []
for pkg in ("onnxruntime", "soundfile", "pypdfium2", "pypdfium2_raw", "_soundfile_data"):
    try:
        binaries += collect_dynamic_libs(pkg)
        datas += collect_data_files(pkg)
    except Exception:  # paquete ausente en esta plataforma: no pasa nada
        pass

hiddenimports = (
    collect_submodules("app")            # varios módulos se importan "perezosamente" dentro de funciones
    + collect_submodules("uvicorn")
    + ["multipart", "python_multipart", "h11", "anyio._backends._asyncio"]
)

a = Analysis(  # noqa: F821
    [str(ROOT / "app" / "desktop.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "pytest", "ruff", "matplotlib", "IPython", "notebook", "PyQt5", "PyQt6", "PySide2", "PySide6"],
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821

windowed = sys.platform in ("darwin", "win32")   # sin ventana de terminal en macOS/Windows
exe = EXE(  # noqa: F821
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="AudioLibroLibre",
    console=not windowed,
    icon=str(ROOT / "packaging" / "icon.icns") if sys.platform == "darwin" and (ROOT / "packaging" / "icon.icns").exists() else None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="AudioLibroLibre")  # noqa: F821

if sys.platform == "darwin":
    app = BUNDLE(  # noqa: F821
        coll,
        name="AudioLibro Libre.app",
        icon=str(ROOT / "packaging" / "icon.icns") if (ROOT / "packaging" / "icon.icns").exists() else None,
        bundle_identifier="org.audiolibrolibre.app",
        version=__version__,
        info_plist={
            "CFBundleName": "AudioLibro Libre",
            "CFBundleDisplayName": "AudioLibro Libre",
            "CFBundleShortVersionString": __version__,
            "LSMinimumSystemVersion": "13.0",     # sin verificar: depende de las ruedas de onnxruntime (ver docs/MAC_APP.md)
            "NSHighResolutionCapable": True,
            "NSAppTransportSecurity": {"NSAllowsLocalNetworking": True},  # la ventana habla con 127.0.0.1
        },
    )
