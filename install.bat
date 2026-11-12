@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title AudioLibro Libre
echo.
echo ==============================================================
echo   AudioLibro Libre - instalador y lanzador para Windows
echo ==============================================================

rem ---------- 1) Python 3.10 o superior ----------
set "PY="
for %%V in (3.12 3.11 3.13 3.10) do (
    if not defined PY (
        py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V"
    )
)
if not defined PY (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1 && set "PY=python"
)
if not defined PY goto :nopython
echo.
echo [1/4] Python encontrado: %PY%

rem ---------- 2) ffmpeg y espeak-ng ----------
set "MISSING="
where ffmpeg >nul 2>&1 || set "MISSING=%MISSING% ffmpeg"
set "ESPEAK_OK="
where espeak-ng >nul 2>&1 && set "ESPEAK_OK=1"
if exist "C:\Program Files\eSpeak NG\espeak-ng.exe" set "ESPEAK_OK=1"
if exist "C:\Program Files (x86)\eSpeak NG\espeak-ng.exe" set "ESPEAK_OK=1"
if not defined ESPEAK_OK set "MISSING=%MISSING% espeak-ng"
if defined MISSING goto :missingtools
echo [2/4] ffmpeg y espeak-ng: correcto.
where tesseract >nul 2>&1 || echo       (Opcional) Tesseract no esta instalado: solo hace falta para PDF escaneados.

rem ---------- 3) Entorno virtual y dependencias ----------
echo [3/4] Preparando el entorno (la primera vez tarda unos minutos y necesita internet)...
if not exist ".venv\Scripts\python.exe" (
    %PY% -m venv .venv
    if errorlevel 1 goto :venvfail
)
fc /b pyproject.toml .venv\pyproject.installed >nul 2>&1
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip >".venv\install.log" 2>&1
    ".venv\Scripts\python.exe" -m pip install --quiet -e . >>".venv\install.log" 2>&1
    if errorlevel 1 goto :pipfail
    copy /y pyproject.toml .venv\pyproject.installed >nul
)

rem ---------- 4) Arranque ----------
if /i "%~1"=="--check" (
    echo [4/4] Instalacion correcta.
    goto :end
)
echo [4/4] Abriendo AudioLibro Libre en tu navegador (http://localhost:8000)
echo       Para cerrar, cierra esta ventana o pulsa Ctrl+C.
".venv\Scripts\python.exe" -m app
goto :end

:nopython
echo.
echo [!] No he encontrado Python 3.10 o superior.
echo     1. Descargalo de https://www.python.org/downloads/windows/
echo     2. Durante la instalacion, marca la casilla "Add python.exe to PATH".
echo     3. Vuelve a hacer doble clic en install.bat
goto :end

:missingtools
echo.
echo [!] Faltan programas necesarios:%MISSING%
echo.
echo   ffmpeg   : abre una ventana de PowerShell y escribe:  winget install Gyan.FFmpeg
echo              (o descargalo de https://www.gyan.dev/ffmpeg/builds/ )
echo   espeak-ng: descarga el instalador .msi de https://github.com/espeak-ng/espeak-ng/releases
echo              e instalalo con las opciones por defecto.
echo.
echo   Despues CIERRA esta ventana y vuelve a hacer doble clic en install.bat
echo   (Con Docker no hace falta instalar nada de esto: mira el README.)
goto :end

:venvfail
echo.
echo [!] No se pudo crear el entorno virtual. Reinstala Python desde python.org y vuelve a intentarlo.
goto :end

:pipfail
echo.
echo [!] Fallo la instalacion de dependencias (detalle en .venv\install.log).
echo     Comprueba tu conexion a internet y vuelve a ejecutar install.bat
goto :end

:end
echo.
pause
endlocal
