from app.jobs import estimate as est


def test_unmeasured_uses_default_and_says_so():
    e = est.estimate(160_000, 20_000, speed=1.0, voice_id="v")
    assert e["rtf_measured"] is False and e["rtf"] == est.DEFAULT_RTF
    assert e["audio_seconds"] == 10_000


def test_speed_measured_per_voice_not_global():
    est.record_rtf("rapida", 100, 2)   # 50× tiempo real
    est.record_rtf("lenta", 100, 50)   # 2×
    assert est.measured_rtf("rapida") == 50 and est.measured_rtf("lenta") == 2
    assert est.measured_rtf("otra") is None
    fast = est.estimate(160_000, 10_000, speed=1.0, voice_id="rapida")
    slow = est.estimate(160_000, 10_000, speed=1.0, voice_id="lenta")
    assert fast["rtf_measured"] and fast["generation_seconds"] < slow["generation_seconds"]


def test_measurement_is_a_moving_average_and_ignores_noise():
    est.record_rtf("v", 100, 10)       # 10×
    est.record_rtf("v", 100, 5)        # 20× -> 0,8·10 + 0,2·20 = 12
    assert est.measured_rtf("v") == 12
    est.record_rtf("v", 0.2, 0.01)     # demasiado corto: no cuenta
    assert est.measured_rtf("v") == 12


def test_faster_reading_needs_less_audio_and_disk():
    normal = est.estimate(160_000, 10_000, speed=1.0)
    quick = est.estimate(160_000, 10_000, speed=1.5)
    assert quick["audio_seconds"] < normal["audio_seconds"] and quick["disk_bytes"] < normal["disk_bytes"]


def test_estimate_endpoint_benchmarks_voice_once(monkeypatch):
    from fastapi.testclient import TestClient

    from app import tts
    from app.web.main import create_app
    from tests.fake_engine import FakeEngine
    eng = FakeEngine()
    eng.installed.add("es_ES-davefx-medium")
    monkeypatch.setitem(tts._FACTORIES, "piper", lambda: eng)
    monkeypatch.setattr(tts, "_INSTANCES", {})
    with TestClient(create_app()) as c:
        jid = c.post("/api/jobs/demo").json()["id"]
        c.put(f"/api/jobs/{jid}/settings", json={"voice": "es_ES-davefx-medium"})
        first = c.get(f"/api/jobs/{jid}/estimate").json()
        calls = len(eng.calls)
        again = c.get(f"/api/jobs/{jid}/estimate").json()
        assert first["rtf_measured"] and again["rtf_measured"]
        assert len(eng.calls) == calls and calls >= 2   # se mide una vez (calentamiento + medida), no en cada consulta
