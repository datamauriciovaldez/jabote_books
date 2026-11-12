#!/usr/bin/env bash
# ENSAYO en Linux de las recetas de macOS (solo para desarrollo): compila LAME, ffmpeg LGPL y espeak-ng con los
# MISMOS scripts y las MISMAS fuentes fijadas (packaging/source-hashes.txt) que usa el Mac. Solo cambian las partes
# propias de macOS (otool, codesign, hdiutil…), que no se pueden ensayar aquí.
# Después, para probar que la app empaquetada usa sus herramientas incluidas, ver docs/MAC_APP.md ("Ensayo en Linux").
# Requiere: build-essential autoconf automake libtool pkg-config (y opcionalmente nasm).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export AUDIOLIBRO_REHEARSAL=1
"$ROOT/tools/mac/build_ffmpeg.sh"
"$ROOT/tools/mac/build_espeak.sh"
echo; echo "==> Ensayo de compilación terminado. Binarios en $ROOT/build/mac/prefix/bin"
