"""Generador mínimo de PDFs para pruebas (sin dependencias): texto Helvetica con posiciones y tamaños."""
from __future__ import annotations

import textwrap
from pathlib import Path

Seg = tuple[str, float, float, float]  # (texto, tamaño, x, y)


def _esc(text: str) -> bytes:
    return text.encode("cp1252").replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def write_pdf(path: Path, pages: list[list[Seg]], outline: list[tuple[str, int]] | None = None) -> Path:
    objs: list[bytes] = []
    n_pages = len(pages)
    first_page_obj = 5
    page_ids = [first_page_obj + 2 * i for i in range(n_pages)]
    outline_root = first_page_obj + 2 * n_pages
    objs.append(b"<< /Type /Catalog /Pages 2 0 R"
                + (f" /Outlines {outline_root} 0 R".encode() if outline else b"") + b" >>")
    kids = " ".join(f"{i} 0 R" for i in page_ids)
    objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>".encode())
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    objs.append(b"<< >>")  # 4: reservado
    for i, segs in enumerate(pages):
        stream = b""
        for text, size, x, y in segs:
            stream += f"BT /F1 {size} Tf {x} {y} Td (".encode() + _esc(text) + b") Tj ET\n"
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {page_ids[i] + 1} 0 R "
                    f"/Resources << /Font << /F1 3 0 R >> >> >>".encode())
        objs.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"endstream")
    if outline:
        first = outline_root + 1
        objs.append(f"<< /Type /Outlines /First {first} 0 R /Last {first + len(outline) - 1} 0 R "
                    f"/Count {len(outline)} >>".encode())
        for k, (title, page) in enumerate(outline):
            nxt = f" /Next {first + k + 1} 0 R" if k + 1 < len(outline) else ""
            prv = f" /Prev {first + k - 1} 0 R" if k else ""
            objs.append(f"<< /Title ({title}) /Parent {outline_root} 0 R /Dest [{page_ids[page]} 0 R /Fit]"
                        f"{nxt}{prv} >>".encode())
    out = b"%PDF-1.4\n"
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(out)
    return path


def book_page(paragraphs: list[str], *, number: int | None = None, header: str | None = None,
              footnote: str | None = None, width: int = 62) -> list[Seg]:
    """Una página con párrafos justificados a `width` caracteres, cabecera, nº de página y nota al pie."""
    segs: list[Seg] = []
    if header:
        segs.append((header, 9, 72, 750))
    y = 700
    for para in paragraphs:
        lines = textwrap.wrap(para, width=width, break_on_hyphens=False)
        for ln in lines:
            segs.append((ln, 12, 72, y))
            y -= 16
        y -= 6 if len(lines[-1]) >= 0.7 * width else 0
    if footnote:
        segs.append((footnote, 8, 72, 100))
    if number is not None:
        segs.append((str(number), 10, 300, 50))
    return segs
