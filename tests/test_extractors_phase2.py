import shutil
import zipfile

import pytest
from docx import Document

from app.errors import UserError
from app.extractors import ocr
from app.extractors.base import extract
from app.extractors.docx import extract_docx
from app.extractors.md import extract_md, strip_markdown
from app.extractors.pdf import extract_pdf
from tests.pdfgen import book_page, write_pdf

SENT = ("Era una tarde tranquila número {i} en el pueblo y nadie esperaba que llegase el forastero con su "
        "maleta gris, que traía noticias importantes de la ciudad lejana. ")
_seed = [0]


def para(n=3):
    """Texto distinto en cada llamada (en un libro real las líneas no se repiten página tras página)."""
    out = []
    for _ in range(n):
        _seed[0] += 1
        out.append(SENT.format(i=_seed[0]))
    return "".join(out).strip()


def sample_pdf(tmp_path, with_header=True, footnote_on=None):
    pages = []
    for i in range(8):
        paras = []
        if i in (0, 4):
            paras.append(f"Capítulo {1 if i == 0 else 2}")
        paras += [para(2), "Esta es una línea corta final."] if i % 2 else [para(3)]
        pages.append(book_page(paras, number=i + 1, header="Mi Libro de Prueba - Ana Autora" if with_header else None,
                               footnote="1 Esta es una nota al pie de página." if i == footnote_on else None))
    return write_pdf(tmp_path / "libro.pdf", pages)


# ----------------------------------------------------------------------------- PDF
def test_pdf_removes_headers_page_numbers_and_finds_chapters(tmp_path):
    book = extract_pdf(sample_pdf(tmp_path))
    assert [c.title for c in book.chapters] == ["Capítulo 1", "Capítulo 2"]
    text = "\n".join(c.text for c in book.chapters)
    assert "Mi Libro de Prueba" not in text          # cabecera repetida
    assert not any(ln.strip().isdigit() for ln in text.splitlines())  # nº de página
    assert "forastero con su maleta gris" in text    # el texto sí está


def test_pdf_paragraphs_are_unwrapped(tmp_path):
    book = extract_pdf(sample_pdf(tmp_path))
    first = book.chapters[0].text.split("\n\n")[0]
    assert "\n" not in first and first.startswith("Era una tarde tranquila número")


def test_pdf_footnotes_in_small_font_removed(tmp_path):
    book = extract_pdf(sample_pdf(tmp_path, footnote_on=2))
    assert "nota al pie" not in "\n".join(c.text for c in book.chapters)


def test_pdf_sentence_continuing_on_next_page_is_joined(tmp_path):
    p1 = book_page(["Capítulo 1", "Primera frase completa y larga para llenar bien la página número uno de este "
                    "libro de prueba, y la segunda frase queda cortada justo al final de la página y continúa"])
    p2 = book_page(["en la página siguiente sin que haya ningún párrafo nuevo aquí. Y luego sigue el texto normal "
                    "del libro con más palabras para que el capítulo tenga contenido suficiente."])
    book = extract_pdf(write_pdf(tmp_path / "c.pdf", [p1, p2]))
    assert "continúa en la página siguiente" in book.chapters[0].text.replace("\n", " ")


def test_pdf_hyphenation_joined(tmp_path):
    line = "Texto del primer capítulo con una infor-"
    pg = [("Capítulo 1", 12, 72, 700), (line, 12, 72, 680),
          ("mación importante que se partió al final de la línea anterior, y sigue la narración con más "
           "palabras hasta completar.", 12, 72, 664)]
    book = extract_pdf(write_pdf(tmp_path / "h.pdf", [pg]))
    assert "información importante" in book.chapters[0].text


def test_pdf_outline_used_when_no_headings(tmp_path):
    pages = [book_page([para(4)], number=1), book_page([para(4)], number=2),
             book_page([para(4)], number=3), book_page([para(4)], number=4)]
    f = write_pdf(tmp_path / "o.pdf", pages, outline=[("Parte Uno", 0), ("Parte Dos", 2)])
    assert [c.title for c in extract_pdf(f).chapters] == ["Parte Uno", "Parte Dos"]


def test_pdf_encrypted(tmp_path):
    from pypdf import PdfReader, PdfWriter
    w = PdfWriter(clone_from=PdfReader(str(sample_pdf(tmp_path))))
    w.encrypt("secreto")
    f = tmp_path / "enc.pdf"
    with f.open("wb") as fh:
        w.write(fh)
    with pytest.raises(UserError) as e:
        extract_pdf(f)
    assert e.value.code == "pdf_encrypted"


def test_pdf_invalid(tmp_path):
    f = tmp_path / "x.pdf"
    f.write_text("no soy un pdf")
    with pytest.raises(UserError) as e:
        extract_pdf(f)
    assert e.value.code == "pdf_invalid"


# ------------------------------------------------------------------------------ OCR
def scanned_pdf(tmp_path):
    """PDF solo de imágenes: se renderiza un PDF de texto y se reempaqueta como imágenes."""
    import pypdfium2 as pdfium
    src = sample_pdf(tmp_path, with_header=False)
    doc = pdfium.PdfDocument(str(src))
    imgs = [doc[i].render(scale=300 / 72).to_pil().convert("L") for i in range(len(doc))]
    out = tmp_path / "scan.pdf"
    imgs[0].save(out, save_all=True, append_images=imgs[1:], resolution=300)
    return out


def test_scanned_pdf_without_tesseract_explains_how(tmp_path, monkeypatch):
    f = scanned_pdf(tmp_path)
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(UserError) as e:
        extract_pdf(f)
    assert e.value.code == "ocr_missing"


@pytest.mark.skipif("spa" not in ocr.installed_languages(), reason="Tesseract + idioma 'spa' no instalados")
def test_scanned_pdf_with_ocr(tmp_path):
    seen = []
    book = extract_pdf(scanned_pdf(tmp_path), "es", lambda stage, d, t: seen.append((stage, d, t)))
    text = " ".join(c.text for c in book.chapters).replace("\n", " ")
    assert "forastero" in text and "maleta" in text and "ocr" in book.warnings
    assert [c.title for c in book.chapters][0].lower().startswith("cap")
    assert ("ocr", 8, 8) in seen


def test_ocr_language_missing(monkeypatch):
    monkeypatch.setattr(ocr, "tesseract_path", lambda: "/usr/bin/tesseract")
    monkeypatch.setattr(ocr, "installed_languages", lambda: {"eng"})
    with pytest.raises(UserError) as e:
        ocr.require("es")
    assert e.value.code == "ocr_lang_missing"


# ----------------------------------------------------------------------------- DOCX
def test_docx_headings_become_chapters(tmp_path):
    d = Document()
    d.core_properties.title = "Mi novela"
    d.core_properties.author = "Ana Autora"
    d.add_heading("Primer capítulo", level=1)
    d.add_paragraph(para(2))
    d.add_heading("Segundo capítulo", level=1)
    d.add_paragraph(para(2))
    f = tmp_path / "n.docx"
    d.save(str(f))
    book = extract_docx(f)
    assert (book.title, book.author) == ("Mi novela", "Ana Autora")
    assert [c.title for c in book.chapters] == ["Primer capítulo", "Segundo capítulo"]


def test_docx_without_heading_styles_uses_text_detection(tmp_path):
    d = Document()
    for n in (1, 2):
        d.add_paragraph(f"Capítulo {n}")
        d.add_paragraph(para(2))
    f = tmp_path / "p.docx"
    d.save(str(f))
    assert [c.title for c in extract(f).chapters] == ["Capítulo 1", "Capítulo 2"]


def test_docx_invalid(tmp_path):
    f = tmp_path / "x.docx"
    f.write_text("no")
    with pytest.raises(UserError) as e:
        extract_docx(f)
    assert e.value.code == "docx_invalid"
    zf = tmp_path / "y.docx"
    with zipfile.ZipFile(zf, "w") as z:
        z.writestr("a.txt", "x")
    with pytest.raises(UserError):
        extract_docx(zf)


# ------------------------------------------------------------------------- Markdown
def test_strip_markdown():
    out = strip_markdown("Un **gran** texto con [enlace](http://x.y) y `código` e ![img](a.png).\n\n> cita\n- item")
    assert out.strip().startswith("Un gran texto con enlace y código e .")
    assert "http" not in out and "**" not in out and ">" not in out and "- item" not in out


def test_md_headings_and_title(tmp_path):
    f = tmp_path / "libro.md"
    f.write_text(f"# Mi Libro\n\n## Uno\n\n{para(2)}\n\n## Dos\n\n{para(2)}\n", encoding="utf-8")
    book = extract_md(f)
    assert book.title == "Mi Libro" and [c.title for c in book.chapters] == ["Uno", "Dos"]


def test_header_with_page_number_variants_removed_but_body_lines_kept():
    from app.cleaning.pages import remove_repeated
    pages = [[f"{i + 1} CAPÍTULO DE PRUEBA", f"Era una tarde número {i} en el pueblo y nadie esperaba",
              "texto único " + "x" * i, f"Página {i + 1}"] for i in range(6)]
    out = remove_repeated(pages)
    assert all(len(p) == 2 for p in out)
    assert out[0][0].startswith("Era una tarde número 0")
