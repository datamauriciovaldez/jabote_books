#!/usr/bin/env sh
# Comprobación local: estilo (ruff) + pruebas (pytest). No hay CI: se ejecuta a mano.
# Uso:  ./check.sh          (todo)      ./check.sh fast   (sin pruebas lentas)
set -e
cd "$(dirname "$0")"
python -m ruff check .
if [ "$1" = "fast" ]; then python -m pytest -m "not slow"; else python -m pytest; fi
