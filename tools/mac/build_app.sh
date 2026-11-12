#!/usr/bin/env bash
# Construye AudioLibro Libre.app (Apple Silicon), la firma "ad hoc" (gratis) y crea el .dmg.
#
#   ./tools/mac/build_app.sh
#
# Requisitos: macOS en Apple Silicon, Herramientas de Xcode (xcode-select --install) y Homebrew (https://brew.sh).
# Resultado: dist/mac/AudioLibroLibre-<versión>-arm64.dmg  (+ dist/mac/sources/ con el código de ffmpeg/LAME/espeak-ng)
source "$(dirname "$0")/lib.sh"
require_macos_arm64
cd "$ROOT"
VER="$(python3 -c 'import re;print(re.search(r"^version = \"(.+?)\"", open("pyproject.toml").read(), re.M).group(1))')"
DIST="$ROOT/dist/mac"; mkdir -p "$DIST"

# ---- 1) Herramientas
command -v xcode-select >/dev/null && xcode-select -p >/dev/null 2>&1 || fail "Faltan las herramientas de Xcode. Ejecuta:  xcode-select --install"
command -v brew >/dev/null || fail "Falta Homebrew (https://brew.sh). Es necesario para compilar espeak-ng."
for t in autoconf automake pkg-config; do command -v "$t" >/dev/null || { say "Instalando $t con Homebrew"; brew install "$t"; }; done
# En macOS el comando `libtool` es de Apple (otra herramienta); el de GNU instalado con Homebrew es `glibtoolize`.
command -v glibtoolize >/dev/null || { say "Instalando libtool (GNU) con Homebrew"; brew install libtool; }

# ---- 2) Python (3.10-3.13, para arm64)
PY=""
for cand in python3.12 python3.11 python3.13 python3.10 python3; do
    if command -v "$cand" >/dev/null 2>&1 && "$cand" -c 'import sys,platform; sys.exit(0 if (3,10)<=sys.version_info[:2]<=(3,13) and platform.machine()=="arm64" else 1)' 2>/dev/null; then PY="$cand"; break; fi
done
[ -n "$PY" ] || fail "No encuentro Python 3.10–3.13 para Apple Silicon. Instálalo con:  brew install python@3.12"
say "Usando $($PY --version) ($PY)"

# ---- 3) ffmpeg (LGPL) y espeak-ng (GPL-3) propios, si no están ya compilados
[ -x "$PREFIX/bin/ffmpeg" ]    || "$ROOT/tools/mac/build_ffmpeg.sh"
[ -x "$PREFIX/bin/espeak-ng" ] || "$ROOT/tools/mac/build_espeak.sh"

# ---- 4) Entorno de construcción e icono
say "Preparando el entorno de construcción (necesita internet)"
[ -x "$WORK/venv/bin/python" ] || "$PY" -m venv "$WORK/venv"
"$WORK/venv/bin/python" -m pip install --quiet --upgrade pip
"$WORK/venv/bin/python" -m pip install --quiet -e ".[mac]" >"$WORK/pip.log" 2>&1 || { tail -n 20 "$WORK/pip.log"; fail "Falló la instalación de dependencias (ver $WORK/pip.log)"; }
ICONSET="$WORK/icon.iconset"; mkdir -p "$ICONSET"
for s in 16 32 64 128 256 512; do
    sips -z $s $s "$ROOT/packaging/icon-1024.png" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
    sips -z $((s*2)) $((s*2)) "$ROOT/packaging/icon-1024.png" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$ROOT/packaging/icon.icns"

# ---- 5) PyInstaller
say "Construyendo la app (unos minutos)"
rm -rf "$WORK/dist" "$WORK/pyi-work"
"$WORK/venv/bin/python" -m PyInstaller --noconfirm --distpath "$WORK/dist" --workpath "$WORK/pyi-work" packaging/audiolibro.spec >"$WORK/pyinstaller.log" 2>&1 \
    || { tail -n 30 "$WORK/pyinstaller.log"; fail "PyInstaller falló (ver $WORK/pyinstaller.log)"; }
APP="$WORK/dist/AudioLibro Libre.app"; [ -d "$APP" ] || fail "No se generó la .app (ver $WORK/pyinstaller.log)"

# ---- 6) Añadir ffmpeg, espeak-ng, datos y licencias dentro de la app
say "Incluyendo ffmpeg, espeak-ng y licencias"
RES="$APP/Contents/Resources"; mkdir -p "$RES/bin" "$RES/licenses"
cp "$PREFIX/bin/ffmpeg" "$PREFIX/bin/espeak-ng" "$RES/bin/"
DATA="$PREFIX/share/espeak-ng-data"; [ -d "$DATA" ] || DATA="$(find "$PREFIX" -type d -name espeak-ng-data | head -1)"
cp -R "$DATA" "$RES/espeak-ng-data"
cp "$PREFIX"/licenses/* "$RES/licenses/"
cp "$ROOT/packaging/THIRD_PARTY_NOTICES.md" "$ROOT/packaging/source-hashes.txt" "$ROOT/LICENSE" "$ROOT/LICENSES.md" "$RES/licenses/"

# ---- 7) Firma "ad hoc" (gratuita; Apple Silicon la exige para ejecutar) — cada ejecutable y luego la app
say "Firmando (ad hoc)"
codesign --force --sign - "$RES/bin/ffmpeg" "$RES/bin/espeak-ng"
codesign --force --deep --sign - "$APP"
codesign --verify --deep --strict "$APP" || fail "La firma ad hoc no es válida."

# ---- 8) Autoprueba de la app empaquetada (sin ventana)
say "Autoprueba de la app empaquetada"
"$APP/Contents/MacOS/AudioLibroLibre" --self-test 2>&1 | tee "$WORK/selftest.txt"
grep -q "RESULTADO: todo correcto" "$WORK/selftest.txt" || fail "La autoprueba falló. Envía $WORK/selftest.txt para revisarlo."

# ---- 9) DMG y fuentes correspondientes (obligatorio por la GPL/LGPL: se publican junto al .dmg)
say "Creando el .dmg"
STAGE="$WORK/dmg"; rm -rf "$STAGE"; mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"; ln -s /Applications "$STAGE/Applications"
cat > "$STAGE/README.txt" <<TXT
AudioLibro Libre $VER

ENGLISH
1. Drag "AudioLibro Libre" into the Applications folder.
2. On first launch, macOS states that it cannot verify the application is free of malicious software (it is not
   signed with a paid developer certificate). To open it: System Settings > Privacy & Security > scroll to the
   message about "AudioLibro Libre" > "Open Anyway". This is needed only once.
3. The user's book never leaves the Mac. More information: https://github.com/datamauriciovaldez/jabote_books

ESPAÑOL
1. Arrastre "AudioLibro Libre" a la carpeta Aplicaciones.
2. En el primer inicio, macOS indica que no puede comprobar que la aplicación esté libre de software malicioso (no
   está firmada con un certificado de desarrollador de pago). Para abrirla: Ajustes del Sistema > Privacidad y
   seguridad > desplácese hasta el mensaje sobre "AudioLibro Libre" > "Abrir igualmente". Solo es necesario una vez.
3. El libro del usuario nunca sale del Mac. Más información: https://github.com/datamauriciovaldez/jabote_books
TXT
DMG="$DIST/AudioLibroLibre-$VER-arm64.dmg"; rm -f "$DMG"
hdiutil create -volname "AudioLibro Libre" -srcfolder "$STAGE" -ov -format UDZO "$DMG" >/dev/null
mkdir -p "$DIST/sources"; cp "$SRC"/* "$DIST/sources/"
( cd "$DIST" && shasum -a 256 "AudioLibroLibre-$VER-arm64.dmg" > "AudioLibroLibre-$VER-arm64.dmg.sha256" )  # macOS trae shasum
cp "$WORK/selftest.txt" "$DIST/selftest.txt"

say "LISTO"
ls -lh "$DMG"; cat "$DIST/AudioLibroLibre-$VER-arm64.dmg.sha256"
echo "Fuentes a publicar junto al .dmg: $DIST/sources/"
echo "Para probarla: open \"$APP\""
