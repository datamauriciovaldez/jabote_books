import json
import shutil
import subprocess
import zipfile

import pytest

from app import tts
from app.errors import UserError
from app.export.mp3 import export_mp3, make_zip, safe_name
from app.jobs.runner import JobRunner
from app.jobs.store import create_job, update_job
from tests.fake_engine import FakeEngine
from tests.test_jobs import make_book

pytestmark = pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
                                reason="ffmpeg/ffprobe no instalados")


@pytest.fixture
def finished_job(monkeypatch):
    eng = FakeEngine()
    monkeypatch.setitem(tts._FACTORIES, "piper", lambda: eng)
    monkeypatch.setattr(tts, "_INSTANCES", {})
    book = make_book(2, 2)
    book.author = "Ana Autora"
    job = create_job(book, "x.txt")
    update_job(job["id"], lambda j: j["settings"].update(voice="es_ES-davefx-medium"))
    eng.installed.add("es_ES-davefx-medium")
    r = JobRunner()
    r.start(job["id"])
    assert r.join(job["id"]) == "done"
    return job["id"]


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:format_tags",
                          "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)["format"]


def test_safe_name():
    assert safe_name("Capítulo I: ¿Qué/trata?") == "Capitulo I Quetrata"


def test_mp3_per_chapter_with_tags_and_zip(finished_job):
    from app.jobs.store import load_job
    job = load_job(finished_job)
    files = export_mp3(job)
    assert [f.name for f in files] == ["01 - Capitulo 1.mp3", "02 - Capitulo 2.mp3"]
    info = probe(files[0])
    assert float(info["duration"]) > 1
    tags = {k.lower(): v for k, v in info["tags"].items()}
    assert tags["title"] == "Capítulo 1" and tags["artist"] == "Ana Autora"
    assert tags["album"] == "Libro" and tags["track"] == "1/2"
    z = make_zip(job, files)
    with zipfile.ZipFile(z) as zf:
        names = zf.namelist()
        assert "CREDITOS.txt" in names and len([n for n in names if n.endswith(".mp3")]) == 2
        assert "CC0-1.0" in zf.read("CREDITOS.txt").decode()


def test_export_refuses_incomplete(finished_job):
    from app.jobs.store import load_job
    update_job(finished_job, lambda j: j["book"]["chapters"][0].update(text="Texto distinto sin generar."))
    with pytest.raises(UserError) as e:
        export_mp3(load_job(finished_job))
    assert e.value.code == "export_incomplete"
