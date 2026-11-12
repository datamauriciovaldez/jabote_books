import pytest

from app.errors import UserError
from app.extractors.base import extract
from app.extractors.epub import extract_epub
from app.extractors.txt import extract_txt
from tests.conftest import make_epub

LONG = "<p>" + "Una frase de relleno para que haya contenido suficiente. " * 5 + "</p>"


def test_txt_sample_book(tmp_path):
    from pathlib import Path
    sample = Path(__file__).parent.parent / "app" / "samples" / "quijote.txt"
    book = extract_txt(sample)
    assert book.title.startswith("Don Quijote")
    assert book.author == "Miguel de Cervantes Saavedra" and book.language == "es"
    assert [c.title.split(".")[0] for c in book.chapters] == ["Capítulo I", "Capítulo VIII"]
    assert "En un lugar de la Mancha" in book.chapters[0].text
    assert "PROJECT GUTENBERG" not in book.chapters[-1].text


def test_txt_latin1_encoding(tmp_path):
    f = tmp_path / "libro.txt"
    f.write_bytes(("Capítulo 1\n\n" + "El niño comió ñandú. " * 10).encode("latin-1"))
    assert "niño" in extract_txt(f).chapters[0].text


def test_epub_chapters_titles_and_metadata(tmp_path):
    f = make_epub(tmp_path / "a.epub", [
        ("c1.xhtml", "Primero", "<h1>Primero</h1>" + LONG + LONG),
        ("c2.xhtml", "Segundo", "<h1>Segundo</h1>" + LONG),
        ("toc.xhtml", "Índice", "<p>Primero</p><p>Segundo</p>"),
    ])
    book = extract_epub(f)
    assert (book.title, book.author, book.language) == ("Libro de prueba", "Ana Autora", "es")
    assert [c.title for c in book.chapters] == ["Primero", "Segundo", "Índice"]
    assert not book.chapters[0].text.startswith("Primero")  # el título no se duplica en el cuerpo
    assert [c.included for c in book.chapters] == [True, True, False]  # índice desmarcado


def test_epub_footnote_refs_removed(tmp_path):
    body = ('<h1>T</h1><p>Texto con nota<sup><a epub:type="noteref" href="#n1">1</a></sup> aquí. ' +
            "Relleno suficiente. " * 5 + '</p><aside epub:type="footnote" id="n1"><p>La nota al pie.</p></aside>')
    book = extract_epub(make_epub(tmp_path / "n.epub", [("c.xhtml", "T", body)]))
    assert "La nota al pie" not in book.chapters[0].text
    assert "nota 1" not in book.chapters[0].text and "nota aquí" in book.chapters[0].text


def test_epub_continuation_file_merged(tmp_path):
    f = make_epub(tmp_path / "m.epub", [
        ("c1.xhtml", "Capítulo uno", "<h1>Capítulo uno</h1>" + LONG),
        ("c1b.xhtml", "", "<p>Continuación sin título del mismo capítulo.</p>"),
    ])
    book = extract_epub(f)
    assert len(book.chapters) == 1 and "Continuación" in book.chapters[0].text


def test_epub_without_toc_uses_headings(tmp_path):
    f = make_epub(tmp_path / "s.epub", [("c1.xhtml", "", "<h2>Mi título</h2>" + LONG)], toc=False)
    assert extract_epub(f).chapters[0].title == "Mi título"


def test_epub_cover(tmp_path):
    f = make_epub(tmp_path / "c.epub", [("c1.xhtml", "T", "<h1>T</h1>" + LONG)], cover=b"\xff\xd8jpgdata")
    book = extract_epub(f)
    assert book.cover == b"\xff\xd8jpgdata" and book.cover_mime == "image/jpeg"


def test_epub_multiple_chapters_in_one_file(tmp_path):
    body = '<h1 id="a">Uno</h1>' + LONG + '<h1 id="b">Dos</h1>' + LONG
    nav = '<li><a href="all.xhtml#a">Uno</a></li><li><a href="all.xhtml#b">Dos</a></li>'
    f = make_epub(tmp_path / "o.epub", [("all.xhtml", "", body)], nav_links_override=nav)
    assert [c.title for c in extract_epub(f).chapters] == ["Uno", "Dos"]


def test_invalid_epub(tmp_path):
    f = tmp_path / "x.epub"
    f.write_text("no soy un zip")
    with pytest.raises(UserError) as e:
        extract_epub(f)
    assert e.value.code == "epub_invalid"


def test_unsupported_format(tmp_path):
    f = tmp_path / "x.xyz"
    f.write_text("a")
    with pytest.raises(UserError) as e:
        extract(f)
    assert e.value.code == "unsupported_format"
