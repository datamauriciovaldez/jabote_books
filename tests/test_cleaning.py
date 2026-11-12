from app.cleaning.chapters import split_chapters, strip_gutenberg
from app.cleaning.normalize import (
    clean_chapter_text,
    fix_hyphenation,
    paragraphs_for_speech,
    remove_footnotes,
    remove_page_numbers,
    speech_ready,
)
from app.cleaning.pronunciation import apply_rules, parse_rules
from app.cleaning.sentences import split_long, split_sentences


def test_fix_hyphenation_joins_words():
    assert fix_hyphenation("la infor-\nmación llegó") == "la información llegó"


def test_fix_hyphenation_keeps_real_dashes():
    assert fix_hyphenation("rojo -\nVerde") == "rojo -\nVerde"  # mayúscula: no es corte de palabra


def test_remove_page_numbers():
    txt = "Hola mundo.\n12\n- 13 -\nPágina 14\nAdiós."
    assert remove_page_numbers(txt) == "Hola mundo.\nAdiós."


def test_remove_footnotes():
    out = remove_footnotes("Texto importante[1] y más¹.\n[1] Esta es la nota al pie.\nSigue.")
    assert "[1]" not in out and "¹" not in out and "nota al pie" not in out
    assert "Sigue." in out


def test_hard_wrapped_paragraph_is_unwrapped():
    raw = "Esta es una frase muy larga que el\neditor cortó a mano en dos líneas.\n\nOtro párrafo."
    assert clean_chapter_text(raw).split("\n\n") == [
        "Esta es una frase muy larga que el editor cortó a mano en dos líneas.", "Otro párrafo."]


def test_dialogue_lines_stay_separate():
    raw = "—Hola.\n—¿Qué tal?\n—Bien."
    assert clean_chapter_text(raw).split("\n\n") == ["—Hola.", "—¿Qué tal?", "—Bien."]


def test_speech_ready_dialogue_dash():
    assert speech_ready("—¿Qué gigantes? —dijo Sancho.") == "¿Qué gigantes?, dijo Sancho."


def test_paragraphs_for_speech_adds_final_stop():
    assert paragraphs_for_speech("Capítulo uno\n\nHola.") == ["Capítulo uno.", "Hola."]


def test_chapters_detected_with_subtitle():
    text = ("Capítulo I\nQue trata de algo\n\n" + "Texto largo. " * 20 +
            "\n\nCapítulo II\n\n" + "Más texto aquí. " * 20)
    ch = split_chapters(text)
    assert [c.title for c in ch] == ["Capítulo I. Que trata de algo", "Capítulo II"]


def test_toc_entries_without_body_are_skipped():
    text = "Capítulo I\n\nCapítulo II\n\nCapítulo I\n\n" + "Contenido real. " * 20
    ch = split_chapters(text)
    assert len(ch) == 1 and ch[0].title == "Capítulo I"


def test_lone_numbers_are_not_chapters_unless_sequential():
    pages = "Texto.\n\n12\n\nMás texto.\n\n47\n\nFin."
    assert len(split_chapters(pages)) == 1
    seq = "\n\n".join(f"{n}\n\n" + "Contenido del capítulo. " * 5 for n in (1, 2, 3))
    assert [c.title for c in split_chapters(seq)] == ["1", "2", "3"]


def test_no_chapters_returns_single():
    ch = split_chapters("Solo un texto sin encabezados.", "Mi libro")
    assert len(ch) == 1 and ch[0].title == "Mi libro"


def test_markdown_headings():
    text = "# Uno\n\n" + "a " * 30 + "\n\n## Dos\n\n" + "b " * 30
    assert [c.title for c in split_chapters(text)] == ["Uno", "Dos"]


def test_strip_gutenberg():
    t = ("licencia\n*** START OF THE PROJECT GUTENBERG EBOOK X ***\ncontenido\n"
         "*** END OF THE PROJECT GUTENBERG EBOOK X ***\npie")
    assert strip_gutenberg(t).strip() == "contenido"


def test_sentences_respect_abbreviations():
    s = split_sentences("El Dr. García llegó a las 3.5 horas. Dijo: ¡Hola! Luego se fue.")
    assert s == ["El Dr. García llegó a las 3.5 horas.", "Dijo: ¡Hola!", "Luego se fue."]


def test_sentences_initials():
    assert split_sentences("J. R. Tolkien escribió mucho. Fin.") == ["J. R. Tolkien escribió mucho.", "Fin."]


def test_split_long_keeps_all_text():
    long = ", ".join(["palabra " * 8] * 12)
    parts = split_long(long, 120)
    assert all(len(p) <= 120 for p in parts)
    assert " ".join(parts).replace(",", "").split() == long.replace(",", "").split()


def test_pronunciation_whole_word_and_case():
    rules = parse_rules([{"source": "ONU", "spoken": "onu"}, {"source": "", "spoken": "x"}])
    assert apply_rules("La ONU y la ONUDI", rules) == "La onu y la ONUDI"
    ci = parse_rules([{"source": "hola", "spoken": "ola", "case_sensitive": False}])
    assert apply_rules("Hola, hola", ci) == "ola, ola"
