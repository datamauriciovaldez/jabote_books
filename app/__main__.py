"""Arranque: `python -m app` abre el navegador con la aplicación."""
from __future__ import annotations

import os
import threading
import webbrowser

import uvicorn


def main() -> None:
    host = os.environ.get("AUDIOLIBRO_HOST", "127.0.0.1")
    port = int(os.environ.get("AUDIOLIBRO_PORT", "8000"))
    url = f"http://{'localhost' if host in ('0.0.0.0', '127.0.0.1') else host}:{port}"  # noqa: S104
    if not os.environ.get("AUDIOLIBRO_NO_BROWSER"):
        threading.Timer(1.5, webbrowser.open, args=(url,)).start()
    print(f"\n  AudioLibro Libre está listo en {url}\n  (para cerrar, pulsa Ctrl+C)\n")
    uvicorn.run("app.web.main:app", host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
