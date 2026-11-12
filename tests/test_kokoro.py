import json
import os

import numpy as np
import pytest

from app.config import voices_dir
from app.errors import NotFound
from app.tts import get_engine, kokoro
from app.tts.phonemize import espeak_binary


class FakeSession:
    """Sustituye a onnxruntime: registra las entradas y devuelve 0,1 s de audio por token."""

    def __init__(self):
        self.feeds = []

    def run(self, _names, feed):
        self.feeds.append(feed)
        n = feed["input_ids"].shape[1]
        return [np.full((1, int(2400 * n)), 0.2, dtype=np.float32)]


@pytest.fixture
def engine():
    return get_engine("kokoro").__class__()  # instancia limpia (sin sesión cargada)


def install_fake_files(voice_id="ef_dora", rows=510):
    d = voices_dir() / "kokoro"
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.onnx").write_bytes(b"x")
    rng = np.random.default_rng(0)
    rng.random((rows, 1, 256), dtype=np.float32).tofile(d / f"{voice_id}.bin")


# ---------------------------------------------------------------- catálogo y vocabulario
def test_catalog_is_apache_only_and_spanish_english():
    cat = kokoro._catalog()
    assert cat["license"] == "Apache-2.0" and cat["sample_rate"] == 24000
    assert len(cat["model"]["sha256"]) == 64 and cat["model"]["size_bytes"] > 100_000_000
    assert {v["lang"] for v in cat["voices"]} == {"es", "en"}
    assert {v["id"] for v in cat["voices"] if v["lang"] == "es"} == {"ef_dora", "em_alex", "em_santa"}
    assert all(len(v["sha256"]) == 64 and v["espeak"] in ("es", "en-us", "en-gb") for v in cat["voices"])


def test_vocab_is_consistent_with_the_model():
    vocab = kokoro._vocab()
    assert 0 not in vocab.values()  # el id 0 está reservado: es el relleno que rodea la entrada
    assert len(set(vocab.values())) == len(vocab) == 114 and max(vocab.values()) == 177


def test_tokenize_drops_unknown_symbols_and_truncates():
    assert kokoro.tokenize("a☃b") == [kokoro._vocab()["a"], kokoro._vocab()["b"]]
    assert len(kokoro.tokenize("a" * 1000)) == kokoro.MAX_TOKENS


def test_style_row_is_picked_by_token_count_and_clipped():
    voice = np.arange(510, dtype=np.float32).reshape(510, 1, 1) * np.ones((1, 1, 256), dtype=np.float32)
    assert kokoro.style_for(voice, 10).shape == (1, 256) and kokoro.style_for(voice, 10)[0, 0] == 9
    assert kokoro.style_for(voice, 0)[0, 0] == 0 and kokoro.style_for(voice, 9999)[0, 0] == 509


# ---------------------------------------------------------------- instalación y listado
def test_download_size_counts_shared_model_only_once(engine):
    first = {v.id: v for v in engine.list_voices("es")}["em_alex"]
    assert first.size_bytes > 300_000_000 and not first.installed
    install_fake_files("ef_dora")
    after = {v.id: v for v in engine.list_voices("es")}
    assert after["ef_dora"].installed and after["ef_dora"].size_bytes == 0
    assert 0 < after["em_alex"].size_bytes < 1_000_000 and not after["em_alex"].installed  # solo falta su voz


def test_install_downloads_model_then_voice_with_checksums(engine, monkeypatch):
    calls, seen = [], []

    def fake_download(url, dest, *, expected_size=0, sha256="", progress=None, cancel=None):
        calls.append((url.rsplit("/", 1)[-1], expected_size, sha256))
        dest.write_bytes(b"x")
        if progress:
            progress(expected_size, expected_size)

    monkeypatch.setattr(kokoro, "download_file", fake_download)
    engine.install("em_alex", lambda d, t: seen.append((d, t)))
    assert [c[0] for c in calls] == ["model.onnx", "em_alex.bin"] and all(len(c[2]) == 64 for c in calls)
    assert seen[-1][0] == seen[-1][1] == sum(c[1] for c in calls)   # la barra llega al 100 % exacto
    calls.clear()
    engine.install("ef_dora", None)
    assert [c[0] for c in calls] == ["ef_dora.bin"]                  # el modelo ya estaba: no se baja otra vez


def test_unknown_and_missing_voices(engine):
    with pytest.raises(NotFound) as e:
        engine.voice_info("xx_nadie")
    assert e.value.code == "voice_unknown"
    with pytest.raises(NotFound) as e2:
        engine.synthesize("hola", "ef_dora")
    assert e2.value.code == "voice_not_installed"


# ------------------------------------------------------------------------------ síntesis
@pytest.mark.skipif(espeak_binary() is None, reason="espeak-ng no instalado")
def test_synthesis_feeds_model_like_the_reference(engine):
    install_fake_files()
    engine._session = FakeSession()
    audio = engine.synthesize("Hola, ¿qué tal?", "ef_dora", speed=1.2)
    feed = engine._session.feeds[0]
    ids = feed["input_ids"][0]
    assert audio.sample_rate == 24000 and audio.seconds > 0.3
    assert ids[0] == 0 and ids[-1] == 0 and len(ids) > 5                    # relleno con 0 al principio y al final
    assert feed["style"].shape == (1, 256) and feed["speed"].tolist() == pytest.approx([1.2])
    assert feed["input_ids"].dtype == np.int64 and feed["style"].dtype == np.float32


@pytest.mark.skipif(espeak_binary() is None, reason="espeak-ng no instalado")
def test_long_text_is_batched_within_the_token_limit(engine):
    install_fake_files()
    engine._session = FakeSession()
    text = " ".join(f"Esta es la frase número {i} del texto de prueba, bastante larga." for i in range(40))
    engine.synthesize(text, "ef_dora")
    sizes = [f["input_ids"].shape[1] - 2 for f in engine._session.feeds]
    assert len(sizes) > 1 and max(sizes) <= kokoro.MAX_TOKENS and sum(sizes) > 1000


@pytest.mark.skipif(espeak_binary() is None, reason="espeak-ng no instalado")
def test_symbols_only_text_gives_short_silence(engine):
    install_fake_files()
    engine._session = FakeSession()
    audio = engine.synthesize("...", "ef_dora")
    assert audio.seconds < 0.2 and not engine._session.feeds


def test_credits_for_kokoro():
    from app.export.metadata import credits_text
    job = {"book": {"title": "T", "author": "A"}, "settings": {"engine": "kokoro", "voice": "ef_dora"}}
    txt = credits_text(job)
    assert "ef_dora (Kokoro-82M)" in txt and "Apache-2.0" in txt


# --------------------------------------------- real (opcional: descarga 326 MB; AUDIOLIBRO_TEST_DOWNLOADS=1)
@pytest.mark.slow
@pytest.mark.skipif(not os.environ.get("AUDIOLIBRO_TEST_DOWNLOADS") or espeak_binary() is None,
                    reason="define AUDIOLIBRO_TEST_DOWNLOADS=1 para probar con el modelo real")
def test_real_model_speaks_spanish(engine):
    engine.install("ef_dora")
    audio = engine.synthesize("En un lugar de la Mancha, de cuyo nombre no quiero acordarme.", "ef_dora")
    assert 3 < audio.seconds < 9 and float(np.abs(audio.samples).max()) > 0.05
    json.dumps({"ok": True})
