"""Metadatos ID3 y créditos de licencia de la voz."""
from __future__ import annotations

from typing import Any

from app.tts import catalog


def id3_args(*, title: str, artist: str, album: str, track: int, tracks: int, comment: str) -> list[str]:
    """Argumentos de ffmpeg para las etiquetas de un capítulo."""
    meta = {"title": title, "artist": artist, "album_artist": artist, "album": album,
            "track": f"{track}/{tracks}", "genre": "Audiobook", "comment": comment}
    args: list[str] = []
    for k, v in meta.items():
        if v:
            args += ["-metadata", f"{k}={v}"]
    return args


def voice_credit(voice_id: str) -> dict[str, Any]:
    """Datos de licencia de la voz usada (para cumplir la atribución CC-BY)."""
    raw = catalog.get_raw(voice_id)
    return {"voice": voice_id, "license": raw["license"], "dataset": raw["dataset_url"],
            "attribution_required": raw["attribution_required"]}


def credits_text(job: dict[str, Any]) -> str:
    b, s = job["book"], job["settings"]
    c = voice_credit(s["voice"]) if s.get("voice") else None
    lines = [f"{b['title']} — {b['author']}".strip(" —"), "",
             "Audiolibro generado con AudioLibro Libre (MIT), en local y con software libre.", ""]
    if c:
        lines += [f"Voz: {c['voice']} (Piper)", f"Licencia de la voz/datos: {c['license']}",
                  f"Origen de los datos de la voz: {c['dataset'] or 'ver LICENSES.md'}"]
        if c["attribution_required"]:
            lines.append("Esta licencia exige atribución: conserve este texto al distribuir el audio.")
    lines += ["", "Recuerde: debe tener los derechos del libro que convierte."]
    return "\n".join(lines) + "\n"
