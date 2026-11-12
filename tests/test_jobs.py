import pytest

from app import tts
from app.errors import UserError
from app.extractors.base import Book, Chapter
from app.jobs.chunking import chapter_chunks, synthesis_signature
from app.jobs.runner import JobRunner
from app.jobs.store import chunk_dir, create_job, load_job, update_job
from tests.fake_engine import FakeEngine

SIG = synthesis_signature("piper", "v", 0, 1.0)
PARA = "Esta es la primera frase del párrafo. Esta es la segunda frase del párrafo. "


def make_book(n_chapters=2, paras=4):
    text = "\n\n".join(PARA * 3 + f"Fin del párrafo número {i}." for i in range(paras))
    return Book("Libro", "Autor", "es", [Chapter(f"Capítulo {i + 1}", text) for i in range(n_chapters)])


@pytest.fixture
def engine(monkeypatch):
    eng = FakeEngine()
    monkeypatch.setitem(tts._FACTORIES, "piper", lambda: eng)
    monkeypatch.setattr(tts, "_INSTANCES", {})
    return eng


def new_job(book=None):
    job = create_job(book or make_book(), "libro.txt")
    update_job(job["id"], lambda j: j["settings"].update(voice="fake-voice"))
    return job["id"]


# ------------------------------------------------------------------ fragmentos
def test_chunks_respect_max_size_and_keep_all_text():
    text = "\n\n".join([PARA * 6] * 3)
    chunks = chapter_chunks(1, "T", text, signature=SIG, max_chars=200)
    assert all(len(c.text) <= 200 for c in chunks)
    joined = " ".join(c.text for c in chunks)
    assert joined.count("primera frase") == 18  # 6 por párrafo × 3: no se pierde ni duplica texto
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_paragraph_ends_marked():
    chunks = chapter_chunks(1, "T", "Uno uno uno.\n\nDos dos dos.", signature=SIG, read_title=False)
    assert [c.para_end for c in chunks] == [True, True]


def test_keys_depend_on_text_and_settings():
    a = chapter_chunks(1, "T", "Hola mundo.", signature=SIG, read_title=False)[0]
    b = chapter_chunks(1, "T", "Hola mundo.", signature=SIG, read_title=False)[0]
    c = chapter_chunks(1, "T", "Hola mundo!", signature=SIG, read_title=False)[0]
    d = chapter_chunks(1, "T", "Hola mundo.", signature=synthesis_signature("piper", "v", 0, 1.2),
                       read_title=False)[0]
    assert a.key == b.key and len({a.key, c.key, d.key}) == 3


def test_pronunciation_applied_to_chunk_text():
    ch = chapter_chunks(1, "T", "La ONU decidió.", signature=SIG, read_title=False,
                        rules=[__import__("app.cleaning.pronunciation", fromlist=["Rule"]).Rule("ONU", "o ene u")])
    assert ch[0].text == "La o ene u decidió."


# --------------------------------------------------------------------- cola
def test_full_run_creates_every_chunk(engine):
    r = JobRunner()
    job_id = new_job()
    r.start(job_id)
    assert r.join(job_id) == "done"
    p = r.progress(job_id)
    assert p["done_chunks"] == p["total_chunks"] > 0 and p["percent"] == 100.0
    assert len(engine.calls) == p["total_chunks"]


def test_resume_does_not_regenerate(engine):
    r = JobRunner()
    job_id = new_job()
    r.start(job_id)
    r.join(job_id)
    first = len(engine.calls)
    r.start(job_id)  # segunda ejecución: todo existe
    r.join(job_id)
    assert len(engine.calls) == first


def test_pause_then_resume_keeps_work(engine):
    engine.delay = 0.03
    r = JobRunner()
    job_id = new_job(make_book(3, 6))
    r.start(job_id)
    while r.progress(job_id)["done_chunks"] < 3:
        pass
    r.stop(job_id, "pause")
    assert r.join(job_id) == "paused"
    done_before = r.progress(job_id)["done_chunks"]
    calls_before = len(engine.calls)
    assert 3 <= done_before < r.progress(job_id)["total_chunks"]
    engine.delay = 0
    r.start(job_id)
    assert r.join(job_id) == "done"
    total = r.progress(job_id)["total_chunks"]
    assert len(engine.calls) - calls_before == total - done_before  # solo lo que faltaba
    assert len(set(engine.calls)) <= total


def test_cancel_state(engine):
    engine.delay = 0.03
    r = JobRunner()
    job_id = new_job(make_book(3, 6))
    r.start(job_id)
    r.stop(job_id, "cancel")
    assert r.join(job_id) == "cancelled"


def test_editing_one_chapter_regenerates_only_that_chapter(engine):
    r = JobRunner()
    job_id = new_job()
    r.start(job_id)
    r.join(job_id)
    n = len(engine.calls)
    update_job(job_id, lambda j: j["book"]["chapters"][1].update(text="Texto nuevo distinto del capítulo."))
    r.start(job_id)
    r.join(job_id)
    new_calls = engine.calls[n:]
    assert new_calls == ["Texto nuevo distinto del capítulo."]  # el título sin cambios se reutiliza
    # los ficheros viejos del capítulo editado se borraron: quedan título + texto nuevo
    assert len(list(chunk_dir(job_id, 2).glob("*.flac"))) == 2


def test_excluded_chapters_are_skipped(engine):
    r = JobRunner()
    job_id = new_job()
    update_job(job_id, lambda j: j["book"]["chapters"][0].update(included=False))
    r.start(job_id)
    r.join(job_id)
    assert not any("Capítulo 1" in c for c in engine.calls)


def test_engine_failure_is_reported_not_crashed(engine):
    engine.fail_on = "número 2"
    r = JobRunner()
    job_id = new_job()
    r.start(job_id)
    assert r.join(job_id) == "error"
    err = load_job(job_id)["state"]["error"]
    assert err["code"] == "unexpected" and "boom" in err["detail"]
    engine.fail_on = None
    r.start(job_id)  # tras corregir el problema se reanuda
    assert r.join(job_id) == "done"


def test_start_requires_voice_and_installed(engine):
    r = JobRunner()
    job = create_job(make_book(), "x.txt")
    with pytest.raises(UserError) as e:
        r.start(job["id"])
    assert e.value.code == "voice_not_selected"
    update_job(job["id"], lambda j: j["settings"].update(voice="otra"))
    with pytest.raises(UserError) as e:
        r.start(job["id"])
    assert e.value.code == "voice_not_installed"


def test_recover_marks_running_as_paused(engine):
    r = JobRunner()
    job_id = new_job()
    update_job(job_id, lambda j: j["state"].update(status="running"))
    r.recover()
    assert load_job(job_id)["state"]["status"] == "paused"


def test_interrupted_partial_file_is_cleaned(engine):
    r = JobRunner()
    job_id = new_job()
    junk = chunk_dir(job_id, 1) / "00000-basura.tmp.flac"
    junk.write_bytes(b"x")
    r.start(job_id)
    r.join(job_id)
    assert not junk.exists()
