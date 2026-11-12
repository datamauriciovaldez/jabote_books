#!/usr/bin/env sh
# Crea el paquete de una versión (ZIP + suma de comprobación). Todo es manual y local: no hay CI.
# Uso:  ./tools/make_release.sh            (exige árbol de git limpio y pruebas en verde)
#       ./tools/make_release.sh --allow-dirty   (solo para probar el script; empaqueta lo último commiteado)
set -eu
cd "$(dirname "$0")/.."

VERSION="$(python3 -c 'import re;print(re.search(r"^version = \"(.+?)\"", open("pyproject.toml").read(), re.M).group(1))')"
NAME="audiolibro-libre-$VERSION"

if [ "${1:-}" != "--allow-dirty" ]; then
    [ -z "$(git status --porcelain)" ] || { echo "[!] Hay cambios sin commitear. Haz commit o usa --allow-dirty (solo pruebas)." >&2; exit 1; }
    echo "==> Ejecutando ruff y pytest…"
    ./check.sh
fi

mkdir -p dist
git archive --format=zip --prefix="$NAME/" -o "dist/$NAME.zip" HEAD
( cd dist && { sha256sum "$NAME.zip" 2>/dev/null || shasum -a 256 "$NAME.zip"; } > "$NAME.zip.sha256" )
echo "==> Listo:"
ls -lh "dist/$NAME.zip" "dist/$NAME.zip.sha256"
cat "dist/$NAME.zip.sha256"
echo "Siguiente paso manual: ver docs/RELEASING.md (subir el ZIP a una release de GitHub desde la web)."
