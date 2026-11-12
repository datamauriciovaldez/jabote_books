#!/usr/bin/env bash
# Compila espeak-ng (GPL-3) como programa independiente, estático, con su carpeta de datos.
# Uso (macOS Apple Silicon):  ./tools/mac/build_espeak.sh
source "$(dirname "$0")/lib.sh"
require_macos_arm64
for t in autoconf automake pkg-config; do
    command -v "$t" >/dev/null || fail "Falta '$t'. Ejecuta:  brew install autoconf automake libtool pkg-config"
done
# OJO: en macOS `libtool` es una herramienta de Apple distinta; la de Homebrew se llama `glibtoolize`.
command -v glibtoolize >/dev/null || command -v libtoolize >/dev/null || fail "Falta libtool de GNU. Ejecuta:  brew install libtool"

fetch_source espeak-ng; ES_VER="$VERSION"; ES_TB="$TARBALL"
say "Compilando espeak-ng $ES_VER"
unpack "$ES_TB" "$WORK/build-espeak"
(
  cd "$SRCDIR"
  ./autogen.sh >/dev/null
  ./configure --prefix="$PREFIX" --disable-shared --enable-static \
      --with-pcaudiolib=no --with-sonic=no --with-speechplayer=no --with-mbrola=no >/dev/null
  make -j"$JOBS" >/dev/null
  make install >/dev/null
)
cp "$SRCDIR/COPYING" "$PREFIX/licenses/ESPEAK-NG-COPYING.txt"

[ -x "$PREFIX/bin/espeak-ng" ] || fail "No se generó $PREFIX/bin/espeak-ng"
DATA="$PREFIX/share/espeak-ng-data"; [ -d "$DATA" ] || DATA="$(find "$PREFIX" -type d -name espeak-ng-data | head -1)"
[ -d "$DATA" ] || fail "No se encontró la carpeta espeak-ng-data tras instalar."
assert_self_contained "$PREFIX/bin/espeak-ng"
OUT="$(ESPEAK_DATA_PATH="$(dirname "$DATA")" "$PREFIX/bin/espeak-ng" -q --ipa -v es "hola mundo")"
[ -n "$OUT" ] || fail "espeak-ng no produce fonemas con su carpeta de datos."
say "espeak-ng listo: «hola mundo» → $OUT"
