#!/usr/bin/env sh
# AudioLibro Libre — instalador y lanzador para Linux y macOS (sin Docker).
#   ./install.sh          instala lo necesario (la primera vez) y abre la aplicación
#   ./install.sh --check  solo instala y comprueba que todo está bien, sin abrirla
# Variable opcional: AUDIOLIBRO_PYTHON=python3.12  (elegir el Python a usar)
set -eu
cd "$(dirname "$0")"

CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1

say()  { printf '\n==> %s\n' "$1"; }
fail() { printf '\n[!] %s\n' "$1" >&2; exit 1; }

# ---------------------------------------------------------------- 1) Python 3.10 o superior
say "Buscando Python 3.10 o superior…"
PY=""
for cand in "${AUDIOLIBRO_PYTHON:-}" python3.12 python3.11 python3.13 python3.10 python3 python; do
    [ -n "$cand" ] || continue
    if command -v "$cand" >/dev/null 2>&1 && "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        PY="$cand"; break
    fi
done
if [ -z "$PY" ]; then
    case "$(uname -s)" in
        Darwin) HOW="Instala Python con:  brew install python   (o desde https://www.python.org/downloads/)" ;;
        *)      HOW="Instala Python con:  sudo apt install python3 python3-venv python3-pip   (Debian/Ubuntu)" ;;
    esac
    fail "No he encontrado Python 3.10 o superior. $HOW  Después vuelve a ejecutar ./install.sh"
fi
echo "Usando $($PY --version) ($PY)"

# ------------------------------------------------- 2) ffmpeg y espeak-ng (programas del sistema)
say "Comprobando ffmpeg y espeak-ng…"
MISSING=""
command -v ffmpeg >/dev/null 2>&1 || MISSING="$MISSING ffmpeg"
{ command -v espeak-ng >/dev/null 2>&1 || command -v espeak >/dev/null 2>&1; } || MISSING="$MISSING espeak-ng"
if [ -n "$MISSING" ]; then
    echo "Falta:$MISSING"
    if command -v apt-get >/dev/null 2>&1;  then CMD="sudo apt-get install -y$MISSING"
    elif command -v dnf >/dev/null 2>&1;     then CMD="sudo dnf install -y$MISSING"
    elif command -v pacman >/dev/null 2>&1;  then CMD="sudo pacman -S --needed$MISSING"
    elif command -v brew >/dev/null 2>&1;    then CMD="brew install$MISSING"
    else CMD=""; fi
    if [ -n "$CMD" ] && [ -t 0 ]; then
        printf 'Puedo instalarlo ahora con:\n    %s\n¿Quieres que lo ejecute? [s/N] ' "$CMD"
        read -r ANS || ANS=""
        case "$ANS" in s|S|si|SI|Si|y|Y) sh -c "$CMD" || fail "No se pudo instalar. Ejecuta tú ese comando y vuelve a lanzar ./install.sh" ;;
            *) fail "Instálalo con:  $CMD   y vuelve a ejecutar ./install.sh" ;; esac
    else
        fail "Instala${MISSING} (${CMD:-con el gestor de paquetes de tu sistema}) y vuelve a ejecutar ./install.sh"
    fi
fi
echo "ffmpeg y espeak-ng: correcto."
command -v tesseract >/dev/null 2>&1 || echo "(Opcional) Tesseract no está instalado: solo hace falta para PDFs escaneados. Linux: sudo apt install tesseract-ocr tesseract-ocr-spa · Mac: brew install tesseract tesseract-lang"

# ------------------------------------------------------------------ 3) Entorno virtual y dependencias
say "Preparando el entorno (la primera vez tarda unos minutos y necesita internet)…"
[ -x .venv/bin/python ] || "$PY" -m venv .venv || fail "No se pudo crear el entorno virtual. En Debian/Ubuntu instala:  sudo apt install python3-venv"
if ! cmp -s pyproject.toml .venv/pyproject.installed 2>/dev/null; then
    # La salida de pip (avisos técnicos incluidos) va a un registro; solo se muestra si algo falla.
    { .venv/bin/python -m pip install --quiet --upgrade pip && .venv/bin/python -m pip install --quiet -e . ; } >.venv/install.log 2>&1 \
        || { tail -n 15 .venv/install.log; fail "Falló la instalación de dependencias (detalle en .venv/install.log). Comprueba tu conexión a internet y vuelve a ejecutar ./install.sh"; }
    cp pyproject.toml .venv/pyproject.installed
fi
echo "Dependencias instaladas."

# ------------------------------------------------------------------------------------ 4) Arranque
if [ "$CHECK_ONLY" -eq 1 ]; then
    .venv/bin/python - <<'PYEOF'
from app.tts.phonemize import espeak_binary
import shutil
assert shutil.which("ffmpeg") and espeak_binary(), "faltan ffmpeg o espeak-ng"
import app.web.main  # noqa: F401
print("Todo correcto.")
PYEOF
    exit 0
fi
say "Abriendo AudioLibro Libre en tu navegador (http://localhost:8000). Para cerrar, pulsa Ctrl+C."
exec .venv/bin/python -m app
