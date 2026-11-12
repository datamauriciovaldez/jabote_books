#!/usr/bin/env bash
# Funciones comunes de los scripts de macOS (se cargan con `source`). No se ejecuta directamente.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK="$ROOT/build/mac"
SRC="$WORK/src"          # tarballs descargados (también son la "fuente correspondiente" que se publica)
PREFIX="$WORK/prefix"    # resultado: bin/ffmpeg, bin/espeak-ng, share/espeak-ng-data, licenses/
HASHES="${HASHES:-$ROOT/packaging/source-hashes.txt}"
# AUDIOLIBRO_REHEARSAL=1: ensayo en Linux de las recetas de compilación (solo para desarrollo; ver tools/mac/rehearse_linux.sh)
REHEARSAL="${AUDIOLIBRO_REHEARSAL:-0}"
is_mac() { [ "$(uname -s)" = "Darwin" ]; }
JOBS="$(sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 4)"
mkdir -p "$SRC" "$PREFIX/bin" "$PREFIX/licenses"

# sed -i portable (BSD en macOS, GNU en Linux)
sed_inplace() { if is_mac; then sed -i '' "$@"; else sed -i "$@"; fi; }

# SHA-256 de un archivo (macOS trae shasum; Linux suele traer sha256sum)
sha256_of() { if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | awk '{print $1}'; else sha256sum "$1" | awk '{print $1}'; fi; }

say()  { printf '\n==> %s\n' "$1"; }
fail() { printf '\n[!] %s\n' "$1" >&2; exit 1; }

require_macos_arm64() {
    if [ "$REHEARSAL" = "1" ]; then say "ENSAYO en $(uname -s)/$(uname -m): no se genera nada utilizable en macOS"; return 0; fi
    [ "$(uname -s)" = "Darwin" ] || fail "Este script es solo para macOS."
    [ "$(uname -m)" = "arm64" ] || fail "Está pensado para Apple Silicon (arm64); este Mac es $(uname -m)."
}

# fetch_source NOMBRE -> descarga (si falta), verifica el SHA-256 y deja la ruta del tarball en $TARBALL / versión en $VERSION
fetch_source() {
    local name="$1" line sha url
    line="$(grep -E "^$name " "$HASHES" | head -1)" || true
    [ -n "$line" ] || fail "No hay entrada para '$name' en packaging/source-hashes.txt"
    VERSION="$(echo "$line" | awk '{print $2}')"; sha="$(echo "$line" | awk '{print $3}')"; url="$(echo "$line" | awk '{print $4}')"
    case "$url" in *.tar.xz) TARBALL="$SRC/$name-$VERSION.tar.xz" ;; *) TARBALL="$SRC/$name-$VERSION.tar.gz" ;; esac
    if [ ! -f "$TARBALL" ]; then
        say "Descargando $name $VERSION"
        curl -fL --retry 3 -o "$TARBALL.part" "$url" || fail "No se pudo descargar $url (¿cambió la versión o la dirección? Edita packaging/source-hashes.txt)"
        mv "$TARBALL.part" "$TARBALL"
    fi
    local got; got="$(sha256_of "$TARBALL")"
    if [ "$sha" = "UNPINNED" ]; then
        printf '\n[aviso] %s %s no tiene hash fijado. SHA-256 calculado:\n        %s\n        Compáralo con la web oficial y escríbelo en packaging/source-hashes.txt.\n' "$name" "$VERSION" "$got"
        [ "${AUDIOLIBRO_TRUST_NEW_SOURCES:-0}" = "1" ] || fail "Para continuar sin hash fijado ejecuta: AUDIOLIBRO_TRUST_NEW_SOURCES=1 $0"
    elif [ "$sha" != "$got" ]; then
        rm -f "$TARBALL"; fail "El SHA-256 de $name no coincide (esperado $sha, obtenido $got). Se ha borrado la descarga."
    fi
}

# unpack TARBALL DESTINO -> deja el código en un directorio limpio y devuelve su ruta en $SRCDIR
unpack() {
    local tb="$1" dest="$2"
    rm -rf "$dest"; mkdir -p "$dest"
    tar -xf "$tb" -C "$dest" --strip-components=1
    SRCDIR="$dest"
}

# Comprueba que un ejecutable solo depende de bibliotecas del sistema (así es autónomo dentro de la .app)
assert_self_contained() {
    local bad
    if is_mac; then
        bad="$(otool -L "$1" | tail -n +2 | awk '{print $1}' | grep -v -E '^(/usr/lib/|/System/Library/)' || true)"
    else
        bad="$(ldd "$1" 2>&1 | grep -v -E 'linux-vdso|ld-linux|libc\.so|libm\.so|libdl\.so|libpthread|librt\.so|statically linked|not a dynamic' | awk '{print $1}' | grep . || true)"
    fi
    [ -z "$bad" ] || fail "$1 depende de bibliotecas externas que no irán dentro de la app:
$bad"
}
