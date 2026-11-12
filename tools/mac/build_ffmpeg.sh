#!/usr/bin/env bash
# Compila un ffmpeg LGPL mínimo (solo lo que usa la app: AAC, MP3 con LAME, FLAC, loudnorm, mp4, concat).
# SIN componentes GPL ni "nonfree": así se puede redistribuir dentro de la .app cumpliendo la LGPL.
# Uso (macOS Apple Silicon):  ./tools/mac/build_ffmpeg.sh
source "$(dirname "$0")/lib.sh"
require_macos_arm64
command -v clang >/dev/null || command -v cc >/dev/null || fail "Faltan las herramientas de Xcode. Ejecuta:  xcode-select --install"
command -v make  >/dev/null || fail "Falta 'make' (Herramientas de línea de comandos de Xcode)."

# ---- LAME (codificador MP3; LGPL-2), estático y en nuestro prefijo para que ffmpeg quede autónomo
fetch_source lame; LAME_VER="$VERSION"; LAME_TB="$TARBALL"
say "Compilando LAME $LAME_VER"
unpack "$LAME_TB" "$WORK/build-lame"
LAME_PREFIX="$WORK/lame-prefix"
if is_mac; then
    # config.guess/sub de LAME 3.100 no conocen Apple Silicon: se sustituyen por los de automake.
    AM_DIR="$(ls -d "$(brew --prefix automake 2>/dev/null)"/share/automake-* 2>/dev/null | head -1 || true)"
    [ -n "$AM_DIR" ] || fail "Falta automake. Ejecuta:  brew install automake autoconf libtool pkg-config"
    cp "$AM_DIR/config.guess" "$AM_DIR/config.sub" "$SRCDIR/"
fi
# Parche conocido (también lo aplica Homebrew): símbolo inexistente que rompe el enlazado en macOS reciente.
sed_inplace '/lame_init_old/d' "$SRCDIR/include/libmp3lame.sym"
( cd "$SRCDIR" && ./configure --prefix="$LAME_PREFIX" --disable-shared --enable-static --disable-frontend \
      --disable-dependency-tracking >/dev/null && make -j"$JOBS" >/dev/null && make install >/dev/null )
cp "$SRCDIR/COPYING" "$PREFIX/licenses/LAME-COPYING.txt"

# ---- ffmpeg (LGPL-2.1+)
fetch_source ffmpeg; FF_VER="$VERSION"; FF_TB="$TARBALL"
say "Compilando ffmpeg $FF_VER (LGPL, sin GPL ni nonfree; unos minutos)"
unpack "$FF_TB" "$WORK/build-ffmpeg"
ARCH_FLAGS="--arch=arm64"
if ! is_mac; then ARCH_FLAGS=""; command -v nasm >/dev/null || ARCH_FLAGS="--disable-x86asm"; fi   # (ensayo en Linux)
CONFIG_FLAGS="--prefix=$PREFIX $ARCH_FLAGS --disable-gpl --disable-nonfree --disable-autodetect --disable-doc \
--disable-ffplay --disable-ffprobe --disable-network --disable-debug --enable-static --disable-shared \
--enable-libmp3lame --extra-cflags=-I$LAME_PREFIX/include --extra-ldflags=-L$LAME_PREFIX/lib"
( cd "$SRCDIR" && ./configure $CONFIG_FLAGS >/dev/null && make -j"$JOBS" >/dev/null && make install >/dev/null )
cp "$SRCDIR/COPYING.LGPLv2.1" "$PREFIX/licenses/FFMPEG-COPYING.LGPLv2.1.txt"
echo "$CONFIG_FLAGS" > "$PREFIX/licenses/ffmpeg-configure-flags.txt"

# ---- comprobaciones: autónomo, LGPL y con lo que necesita la app
# (se guarda la salida y se comprueba con `case`: `ffmpeg | grep -q` falla al azar por SIGPIPE con `set -o pipefail`)
FF="$PREFIX/bin/ffmpeg"
assert_self_contained "$FF"
VERSION_OUT="$("$FF" -hide_banner -version 2>&1)"
case "$VERSION_OUT" in *--enable-gpl*) fail "El ffmpeg compilado es GPL (no debería)." ;; esac
ENCODERS="$("$FF" -hide_banner -encoders 2>&1)"
for e in libmp3lame aac flac; do
    case "$ENCODERS" in *" $e "*) ;; *) fail "Falta el codificador $e" ;; esac
done
FILTERS="$("$FF" -hide_banner -filters 2>&1)"
case "$FILTERS" in *loudnorm*) ;; *) fail "Falta el filtro loudnorm" ;; esac
say "ffmpeg listo: $FF ($(echo "$VERSION_OUT" | head -1))"
