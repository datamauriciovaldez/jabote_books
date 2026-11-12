#!/usr/bin/env bash
# ENSAYO en Linux de las recetas de macOS (solo para desarrollo): compila ffmpeg LGPL y espeak-ng con los
# MISMOS scripts que usa el Mac, pero con las fuentes de Ubuntu (ffmpeg 6.1.1 y espeak-ng 1.51), y comprueba que
# la app empaquetada los encuentra y funciona sin ffmpeg/espeak-ng del sistema.
# Requiere: build-essential autoconf automake libtool pkg-config (y opcionalmente nasm).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export AUDIOLIBRO_REHEARSAL=1 AUDIOLIBRO_TRUST_NEW_SOURCES=1
export HASHES="$ROOT/build/mac/rehearsal-hashes.txt"
mkdir -p "$ROOT/build/mac"
LAME_LINE="$(grep -E '^lame ' "$ROOT/packaging/source-hashes.txt")"
cat > "$HASHES" <<EOF
$LAME_LINE
ffmpeg 6.1.1 UNPINNED http://archive.ubuntu.com/ubuntu/pool/universe/f/ffmpeg/ffmpeg_6.1.1.orig.tar.xz
espeak-ng 1.51 UNPINNED http://archive.ubuntu.com/ubuntu/pool/universe/e/espeak-ng/espeak-ng_1.51+dfsg.orig.tar.xz
EOF
"$ROOT/tools/mac/build_ffmpeg.sh"
"$ROOT/tools/mac/build_espeak.sh"
echo; echo "==> Ensayo de compilación terminado. Binarios en $ROOT/build/mac/prefix/bin"
