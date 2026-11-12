"""Genera un EPUB de prueba largo (texto sintético en español) para medir rendimiento.

No es un libro real: sirve para probar estructura (capítulos, diálogos, cifras, abreviaturas) y velocidad.

Uso:  python tools/make_test_epub.py salida.epub [palabras=80000] [capitulos=30]
"""
from __future__ import annotations

import random
import sys
import zipfile
from pathlib import Path

NOUNS = "camino río pueblo casa montaña mercado puente jardín barco carta ventana viaje silencio tormenta campo noche".split()
ADJ = "antiguo tranquilo oscuro luminoso estrecho lejano frío inmenso callado pequeño viejo extraño dulce".split()
VERBS = "caminaba miraba esperaba recordaba buscaba escuchaba guardaba temía deseaba contaba cruzaba abría".split()
NAMES = "Lucía Mateo Elena Tomás Clara Andrés Marta Julián Inés Rafael".split()
PLACES = "Valdeolmos Santa Rosa Montealto Puerto Claro Villaseca".split()


def sentence(rng: random.Random) -> str:
    a, b = rng.choice(NOUNS), rng.choice(NOUNS)
    kind = rng.random()
    if kind < 0.25:
        return f"{rng.choice(NAMES)} {rng.choice(VERBS)} el {a} {rng.choice(ADJ)} cerca de {rng.choice(PLACES)}."
    if kind < 0.5:
        return (f"Aquella {rng.choice(['mañana','tarde','noche'])}, el {b} {rng.choice(ADJ)} parecía más "
                f"{rng.choice(ADJ)} que nunca, y nadie en {rng.choice(PLACES)} {rng.choice(VERBS)} sin miedo.")
    if kind < 0.65:
        return f"—{rng.choice(['¿Dónde', '¿Cuándo', '¿Por qué'])} {rng.choice(VERBS)} {rng.choice(NAMES)}? —preguntó {rng.choice(NAMES)}."
    if kind < 0.75:
        return f"Eran las {rng.randint(1, 12)}:{rng.choice(['00', '15', '30', '45'])} cuando el Sr. {rng.choice(NAMES)} llegó con {rng.randint(2, 40)} cartas."
    return (f"El {a} {rng.choice(ADJ)}, que {rng.choice(VERBS)} desde hacía años, "
            f"guardaba un {b} {rng.choice(ADJ)}; sin embargo, {rng.choice(NAMES)} no lo sabía todavía.")


def build(out: Path, words: int, chapters: int, seed: int = 7) -> None:
    rng = random.Random(seed)
    per = words // chapters
    docs = []
    for c in range(1, chapters + 1):
        paras, n = [], 0
        while n < per:
            para = " ".join(sentence(rng) for _ in range(rng.randint(3, 7)))
            paras.append(f"<p>{para}</p>")
            n += len(para.split())
        docs.append((f"c{c:02d}.xhtml", f"Capítulo {c}", f"<h1>Capítulo {c}</h1>\n" + "\n".join(paras)))
    items = "".join(f'<item id="c{i}" href="{f}" media-type="application/xhtml+xml"/>' for i, (f, _, _) in enumerate(docs))
    spine = "".join(f'<itemref idref="c{i}"/>' for i in range(len(docs)))
    opf = ('<?xml version="1.0" encoding="utf-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" '
           'unique-identifier="id"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>El libro largo de prueba</dc:title>'
           '<dc:creator>Autor Sintético</dc:creator><dc:language>es</dc:language><dc:identifier id="id">test-long</dc:identifier></metadata>'
           f'<manifest>{items}<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/></manifest>'
           f"<spine>{spine}</spine></package>")
    nav = ('<html xmlns="http://www.w3.org/1999/xhtml"><body><nav><ol>'
           + "".join(f'<li><a href="{f}">{t}</a></li>' for f, t, _ in docs) + "</ol></nav></body></html>")
    container = ('<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                 '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
    with zipfile.ZipFile(out, "w") as z:
        z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", container)
        z.writestr("OEBPS/content.opf", opf)
        z.writestr("OEBPS/nav.xhtml", nav)
        for f, _, body in docs:
            z.writestr(f"OEBPS/{f}", f'<html xmlns="http://www.w3.org/1999/xhtml"><body>{body}</body></html>')


if __name__ == "__main__":
    build(Path(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 80_000,
          int(sys.argv[3]) if len(sys.argv) > 3 else 30)
