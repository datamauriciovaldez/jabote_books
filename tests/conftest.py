"""Utilidades de prueba: genera EPUBs mínimos y aísla la carpeta de datos."""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

CONTAINER = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>"""


def make_epub(path: Path, chapters: list[tuple[str, str, str]], title="Libro de prueba",
              author="Ana Autora", toc: bool = True, cover: bytes | None = None,
              nav_links_override: str | None = None) -> Path:
    """chapters = [(archivo, titulo_toc, html_body)]"""
    items = "".join(f'<item id="c{i}" href="{f}" media-type="application/xhtml+xml"/>'
                    for i, (f, _, _) in enumerate(chapters))
    spine = "".join(f'<itemref idref="c{i}"/>' for i in range(len(chapters)))
    cover_item = (
        '<item id="cov" href="cover.jpg" media-type="image/jpeg" properties="cover-image"/>' if cover else "")
    opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>{title}</dc:title>
<dc:creator>{author}</dc:creator><dc:language>es</dc:language></metadata>
<manifest>{items}{cover_item}
<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/></manifest>
<spine>{spine}</spine></package>"""
    nav_links = "".join(f'<li><a href="{f}">{t}</a></li>' for f, t, _ in chapters if t)
    if nav_links_override is not None:
        nav_links = nav_links_override
    nav = f'<html xmlns="http://www.w3.org/1999/xhtml"><body><nav><ol>{nav_links}</ol></nav></body></html>'
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr("META-INF/container.xml", CONTAINER)
        z.writestr("OEBPS/content.opf", opf)
        if toc:
            z.writestr("OEBPS/nav.xhtml", nav)
        if cover:
            z.writestr("OEBPS/cover.jpg", cover)
        for f, _, body in chapters:
            z.writestr(f"OEBPS/{f}", f'<html xmlns="http://www.w3.org/1999/xhtml"><body>{body}</body></html>')
    return path


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIOLIBRO_DATA", str(tmp_path / "data"))
    return tmp_path / "data"
