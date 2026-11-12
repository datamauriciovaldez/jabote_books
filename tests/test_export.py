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


def probe_full(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-show_chapters",
                          "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def add_cover(job_id):
    from PIL import Image

    from app.jobs.store import job_path
    Image.new("RGB", (300, 400), (30, 90, 200)).save(job_path(job_id) / "cover.jpg")
    update_job(job_id, lambda j: j["book"].update(cover="cover.jpg"))


def test_m4b_has_chapter_markers_cover_and_metadata(finished_job):
    from app.export.mp3 import export_all
    from app.jobs.store import load_job
    add_cover(finished_job)
    job = load_job(finished_job)
    res = export_all(job, ["m4b"])
    assert res["mp3"] == [] and res["m4b"].suffix == ".m4b"
    info = probe_full(res["m4b"])
    assert [c["tags"]["title"] for c in info["chapters"]] == ["Capítulo 1", "Capítulo 2"]
    marks = [(float(c["start_time"]), float(c["end_time"])) for c in info["chapters"]]
    assert marks[0][0] == 0 and abs(marks[0][1] - marks[1][0]) < 0.01          # capítulos contiguos
    assert abs(marks[-1][1] - float(info["format"]["duration"])) < 0.5         # el último llega al final
    tags = {k.lower(): v for k, v in info["format"]["tags"].items()}
    assert tags["title"] == "Libro" and tags["artist"] == "Ana Autora" and tags["genre"] == "Audiobook"
    kinds = {s["codec_type"]: s for s in info["streams"]}
    assert kinds["audio"]["codec_name"] == "aac" and kinds["video"]["disposition"]["attached_pic"] == 1


def test_m4b_chapter_times_match_audio_lengths(finished_job):
    """Los marcadores salen de las muestras exactas: el capítulo 2 empieza donde acaba el audio del 1."""
    import soundfile as sf

    from app.export.m4b import chapter_marks, measure
    from app.export.mp3 import export_all
    from app.jobs.store import load_job
    export_all(load_job(finished_job), ["mp3"])
    job = load_job(finished_job)
    import pathlib
    import tempfile

    from app.export.mp3 import render_chapter_wavs
    with tempfile.TemporaryDirectory() as tmp:
        wavs = render_chapter_wavs(job, pathlib.Path(tmp))
        chs = [measure(t, w) for t, w in wavs]
        marks = chapter_marks(chs)
        assert marks[1][0] == marks[0][1]
        assert abs(marks[0][1] / 1000 - sf.info(str(wavs[0][1])).duration) < 0.002


def test_all_formats_zip_contains_both(finished_job):
    from app.export.mp3 import export_all, make_zip
    from app.jobs.store import load_job
    job = load_job(finished_job)
    res = export_all(job, ["mp3", "m4b"])
    z = make_zip(job, res["mp3"], res["m4b"])
    names = zipfile.ZipFile(z).namelist()
    assert len([n for n in names if n.endswith(".mp3")]) == 2 and any(n.endswith(".m4b") for n in names)


def test_no_format_selected_is_an_error(finished_job):
    from app.export.mp3 import export_all
    from app.jobs.store import load_job
    with pytest.raises(UserError) as e:
        export_all(load_job(finished_job), [])
    assert e.value.code == "export_format_none"


def test_ffmetadata_escapes_special_characters():
    from pathlib import Path

    from app.export.m4b import ChapterAudio, ffmetadata
    job = {"book": {"title": "A=B; C#D", "author": "X"}}
    out = ffmetadata(job, [ChapterAudio("Uno=1;\\2", Path("a.wav"), 22050, 22050)])
    assert "title=A\\=B\\; C\\#D" in out and "title=Uno\\=1\\;\\\\2" in out and "END=1000" in out


def peak_dbfs(path):
    out = subprocess.run(["ffmpeg", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    summary = out[out.rfind("Summary"):]
    return float(next(ln.split()[1] for ln in summary.splitlines() if ln.strip().startswith("Peak:")))


def test_exports_do_not_clip_and_are_levelled(finished_job):
    """Regresión: con TP=-1.5 el M4B de un libro largo medía +1,1 dBFS (saturaba)."""
    from app.export.mp3 import export_all
    from app.jobs.store import load_job
    res = export_all(load_job(finished_job), ["mp3", "m4b"])
    assert peak_dbfs(res["m4b"]) < -0.3
    assert all(peak_dbfs(f) < -0.3 for f in res["mp3"])


def test_export_progress_reaches_total(finished_job):
    from app.export.mp3 import export_all
    from app.jobs.store import load_job
    seen = []
    export_all(load_job(finished_job), ["mp3", "m4b"], lambda d, t, c: seen.append((d, t)))
    assert seen[-1] == (7, 7) and all(t == 7 for _, t in seen)  # 2 capítulos × (montar+normalizar+mp3) + 1 m4b
    assert [d for d, _ in seen] == sorted(d for d, _ in seen)  # el progreso nunca retrocede
