#!/usr/bin/env bash
# Compila un ffmpeg LGPL mínimo (solo lo que usa la app: AAC, MP3 con LAME, FLAC, loudnorm, mp4, concat).
# SIN componentes GPL ni "nonfree": así se puede redistribuir dentro de la .app cumpliendo la LGPL.
# Uso (macOS Apple Silicon):  ./tools/mac/build_ffmpeg.sh
source "$(dirname "$0")/lib.sh"
require_macos_arm64
command -v clang >/dev/null || fail "Faltan las herramientas de Xcode. Ejecuta:  xcode-select --install"
command -v make  >/dev/null || fail "Falta 'make' (Herramientas de línea de comandos de Xcode)."

# ---- LAME (codificador MP3; LGPL-2), estático y en nuestro prefijo para que ffmpeg quede autónomo
fetch_source lame; LAME_VER="$VERSION"; LAME_TB="$TARBALL"
say "Compilando LAME $LAME_VER"
unpack "$LAME_TB" "$WORK/build-lame"
LAME_PREFIX="$WORK/lame-prefix"
# config.guess/sub de LAME 3.100 no conocen Apple Silicon: se sustituyen por los de automake.
AM_DIR="$(ls -d "$(brew --prefix automake 2>/dev/null)"/share/automake-* 2>/dev/null | head -1 || true)"
[ -n "$AM_DIR" ] || fail "Falta automake. Ejecuta:  brew install automake autoconf libtool pkg-config"
cp "$AM_DIR/config.guess" "$AM_DIR/config.sub" "$SRCDIR/"
# Parche conocido (también lo aplica Homebrew): símbolo inexistente que rompe el enlazado en macOS reciente.
sed -i '' '/lame_init_old/d' "$SRCDIR/include/libmp3lame.sym"
( cd "$SRCDIR" && ./configure --prefix="$LAME_PREFIX" --disable-shared --enable-static --disable-frontend \
      --disable-dependency-tracking >/dev/null && make -j"$JOBS" >/dev/null && make install >/dev/null )
cp "$SRCDIR/COPYING" "$PREFIX/licenses/LAME-COPYING.txt"

# ---- ffmpeg (LGPL-2.1+)
fetch_source ffmpeg; FF_VER="$VERSION"; FF_TB="$TARBALL"
say "Compilando ffmpeg $FF_VER (LGPL, sin GPL ni nonfree; unos minutos)"
unpack "$FF_TB" "$WORK/build-ffmpeg"
CONFIG_FLAGS="--prefix=$PREFIX --arch=arm64 --disable-gpl --disable-nonfree --disable-autodetect --disable-doc \
--disable-ffplay --disable-ffprobe --disable-network --disable-debug --enable-static --disable-shared \
--enable-libmp3lame --extra-cflags=-I$LAME_PREFIX/include --extra-ldflags=-L$LAME_PREFIX/lib"
( cd "$SRCDIR" && ./configure $CONFIG_FLAGS >/dev/null && make -j"$JOBS" >/dev/null && make install >/dev/null )
cp "$SRCDIR/COPYING.LGPLv2.1" "$PREFIX/licenses/FFMPEG-COPYING.LGPLv2.1.txt"
echo "$CONFIG_FLAGS" > "$PREFIX/licenses/ffmpeg-configure-flags.txt"

# ---- comprobaciones: autónomo, LGPL y con lo que necesita la app
assert_self_contained "$PREFIX/bin/ffmpeg"
"$PREFIX/bin/ffmpeg" -hide_banner -version | grep -q -- "--enable-gpl" && fail "El ffmpeg compilado es GPL (no debería)."
for e in libmp3lame aac flac; do "$PREFIX/bin/ffmpeg" -hide_banner -encoders | grep -q " $e " || fail "Falta el codificador $e"; done
"$PREFIX/bin/ffmpeg" -hide_banner -filters | grep -q loudnorm || fail "Falta el filtro loudnorm"
say "ffmpeg listo: $PREFIX/bin/ffmpeg ($("$PREFIX/bin/ffmpeg" -hide_banner -version | head -1))"
