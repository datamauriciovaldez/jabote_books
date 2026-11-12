import io
import shutil
import time
import zipfile

import pytest
from fastapi.testclient import TestClient

from app import tts
from app.jobs.runner import runner
from app.web.main import create_app
from tests.conftest import make_epub
from tests.fake_engine import FakeEngine

LONG = "<p>" + "Una frase de relleno para que haya contenido suficiente. " * 6 + "</p>"


@pytest.fixture
def client(monkeypatch):
    eng = FakeEngine()
    eng.installed.add("es_ES-davefx-medium")
    monkeypatch.setitem(tts._FACTORIES, "piper", lambda: eng)
    monkeypatch.setattr(tts, "_INSTANCES", {})
    with TestClient(create_app()) as c:
        c.engine = eng
        yield c


def wait_done(client, job_id, timeout=20):
    end = time.time() + timeout
    while time.time() < end:
        p = client.get(f"/api/jobs/{job_id}/progress").json()
        if p["status"] not in ("running", "queued"):
            return p
        time.sleep(0.05)
    raise TimeoutError


def test_error_format_is_human_friendly(client):
    r = client.post("/api/jobs", files={"file": ("libro.xyz", b"hola")})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "unsupported_format"
    assert client.get("/api/jobs/noexiste").status_code == 404


def test_demo_book_full_flow(client):
    job = client.post("/api/jobs/demo?lang=es").json()
    assert job["book"]["author"] == "Miguel de Cervantes Saavedra" and len(job["book"]["chapters"]) == 2
    jid = job["id"]
    s = client.put(f"/api/jobs/{jid}/settings", json={"voice": "es_ES-davefx-medium", "speed": 1.1}).json()
    assert s["settings"]["speed"] == 1.1
    est = client.get(f"/api/jobs/{jid}/estimate").json()
    assert est["audio_seconds"] > 30 and est["disk_bytes"] > 0 and est["system"]["cpu_count"] >= 1
    assert client.post(f"/api/jobs/{jid}/start").status_code == 200
    p = wait_done(client, jid)
    assert p["status"] == "done" and p["percent"] == 100
    same = {"voice": "es_ES-davefx-medium", "speed": 1.1}
    assert client.put(f"/api/jobs/{jid}/settings", json=same).status_code == 200  # editable tras terminar
    cid = job["book"]["chapters"][0]["id"]
    prev = client.get(f"/api/jobs/{jid}/chapters/{cid}/preview")
    assert prev.status_code == 200 and prev.content[:4] == b"RIFF"


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg no instalado")
def test_export_and_download_zip(client):
    jid = client.post("/api/jobs/demo").json()["id"]
    client.put(f"/api/jobs/{jid}/settings", json={"voice": "es_ES-davefx-medium"})
    assert client.post(f"/api/jobs/{jid}/export").json()["state"] in ("running", "error")  # incompleto aún
    time.sleep(0.3)
    assert client.get(f"/api/jobs/{jid}/export").json()["error"]["code"] == "export_incomplete"
    client.post(f"/api/jobs/{jid}/start")
    wait_done(client, jid)
    client.post(f"/api/jobs/{jid}/export")
    for _ in range(100):
        st = client.get(f"/api/jobs/{jid}/export").json()
        if st["state"] != "running":
            break
        time.sleep(0.1)
    assert st["state"] == "done" and len(st["files"]) == 2
    z = client.get(f"/api/jobs/{jid}/download/{st['zip']}")
    assert z.status_code == 200
    assert len([n for n in zipfile.ZipFile(io.BytesIO(z.content)).namelist() if n.endswith(".mp3")]) == 2
    assert client.get(f"/api/jobs/{jid}/download/..%2Fjob.json").status_code == 404


def test_upload_epub_and_edit_chapters(client, tmp_path):
    f = make_epub(tmp_path / "b.epub", [("c1.xhtml", "Uno", "<h1>Uno</h1>" + LONG),
                                         ("c2.xhtml", "Dos", "<h1>Dos</h1>" + LONG)])
    job = client.post("/api/jobs", files={"file": ("b.epub", f.read_bytes())}).json()
    assert [c["title"] for c in job["book"]["chapters"]] == ["Uno", "Dos"]
    book = job["book"]
    book["chapters"][1]["included"] = False
    book["chapters"].append({"id": None, "title": "Nuevo", "text": "Texto añadido a mano.", "included": True})
    saved = client.put(f"/api/jobs/{job['id']}/book", json=book).json()
    ids = [c["id"] for c in saved["book"]["chapters"]]
    assert len(set(ids)) == 3 and saved["book"]["chapters"][1]["included"] is False


def test_start_without_voice_gives_actionable_error(client):
    jid = client.post("/api/jobs/demo").json()["id"]
    r = client.post(f"/api/jobs/{jid}/start")
    assert r.status_code == 400 and r.json()["error"]["code"] == "voice_not_selected"


def test_pause_resume_via_api(client):
    client.engine.delay = 0.05
    jid = client.post("/api/jobs/demo").json()["id"]
    client.put(f"/api/jobs/{jid}/settings", json={"voice": "es_ES-davefx-medium"})
    client.post(f"/api/jobs/{jid}/start")
    time.sleep(0.2)
    client.post(f"/api/jobs/{jid}/pause")
    p = wait_done(client, jid)
    assert p["status"] == "paused" and 0 < p["done_chunks"] < p["total_chunks"]
    done = p["done_chunks"]
    calls = len(client.engine.calls)
    client.engine.delay = 0
    client.post(f"/api/jobs/{jid}/start")
    p = wait_done(client, jid)
    assert p["status"] == "done"
    assert len(client.engine.calls) - calls == p["total_chunks"] - done


def test_system_and_voices(client):
    sysinfo = client.get("/api/system").json()
    assert "ffmpeg" in sysinfo and "disk_free_bytes" in sysinfo
    voices = client.get("/api/voices?lang=es").json()
    assert voices and all(v["lang"] == "es" and v["license"] for v in voices)
    assert not any("SA" in v["license"] or "NC" in v["license"] for v in voices)


def test_runner_singleton_exists():
    assert runner is not None


def test_upload_pdf_docx_md_and_scanned_error(client, tmp_path, monkeypatch):
    from docx import Document

    from tests.extractors_text import para
    from tests.pdfgen import book_page, write_pdf
    pages = [book_page(["Capítulo 1", para(2)] if i == 0 else [para(3)], number=i + 1,
                       header="Cabecera del libro") for i in range(5)]
    pdf = write_pdf(tmp_path / "a.pdf", pages)
    job = client.post("/api/jobs", files={"file": ("a.pdf", pdf.read_bytes())}, data={"token": "t1"}).json()
    assert job["book"]["chapters"] and "Cabecera" not in job["book"]["chapters"][0]["text"]
    assert client.get("/api/uploads/t1").json()["total"] == 0  # el progreso se limpia al terminar

    d = Document()
    d.add_heading("Uno", 1)
    d.add_paragraph("Un párrafo de texto bastante largo para que el capítulo tenga contenido suficiente. " * 3)
    d.save(str(tmp_path / "a.docx"))
    j2 = client.post("/api/jobs", files={"file": ("a.docx", (tmp_path / "a.docx").read_bytes())}).json()
    assert j2["book"]["chapters"][0]["title"] == "Uno"

    md = b"# Libro\n\n## A\n\n" + b"Texto del capitulo a con **negrita** y mas palabras para llegar al minimo. " * 2 \
        + b"\n\n## B\n\n" + b"Texto del capitulo b con suficiente contenido para que no se descarte. " * 2
    j3 = client.post("/api/jobs", files={"file": ("a.md", md)}).json()
    assert [c["title"] for c in j3["book"]["chapters"]] == ["A", "B"]

    import shutil

    from tests.test_extractors_phase2 import scanned_pdf
    scan = scanned_pdf(tmp_path)
    monkeypatch.setattr(shutil, "which", lambda name: None)
    r = client.post("/api/jobs", files={"file": ("s.pdf", scan.read_bytes())})
    assert r.status_code == 400 and r.json()["error"]["code"] == "ocr_missing"


def test_system_reports_ocr(client):
    s = client.get("/api/system").json()
    assert "tesseract" in s and ".pdf" in s["supported_formats"] and isinstance(s["ocr_languages"], list)
