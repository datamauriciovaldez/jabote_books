import pytest

from app.tts.phonemize import espeak_binary, phonemize

pytestmark = pytest.mark.skipif(espeak_binary() is None, reason="espeak-ng no instalado")


def test_punctuation_stays_in_place():
    """Regresión: espeak fusionaba cláusulas y la puntuación acababa toda al final."""
    ipa = phonemize("Cuando quiero, como casa, tengo cuatro cosas.", "es")
    first, second, third = [part.strip() for part in ipa.replace(".", ",").split(",")][:3]
    assert ipa.count(",") == 2 and ipa.endswith(".")
    assert first.startswith("kw") and second.startswith("k") and third.startswith("t")
    assert ". ." not in ipa and ", ," not in ipa


def test_sentence_without_punctuation():
    assert phonemize("hola amigo", "es").startswith("ˈola")


def test_only_symbols_gives_no_phonemes():
    assert phonemize("...", "es").replace(".", "").strip() == ""


def test_english_voice_code():
    assert "ð" in phonemize("The weather", "en-us")


def test_phoneme_ids_layout_matches_piper():
    from app.tts.piper import PiperEngine

    idm = {"_": [0], "^": [1], "$": [2], "a": [14], "b": [15]}
    assert PiperEngine._ids("ab x", idm) == [1, 0, 14, 0, 15, 0, 2]  # BOS PAD a PAD b PAD EOS; 'x' y ' ' ignorados
