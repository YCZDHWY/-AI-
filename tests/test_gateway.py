from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from gateway.app import Reading, Store, create_app, utc_now


def sample(**changes):
    return Reading(**({"device_id": "plant-01", "soil_raw": 2300,
                       "soil_percent": 48, "temperature_c": 24,
                       "humidity_percent": 60, "light_lux": 650} | changes))


def test_store_persists_and_filters(tmp_path):
    path = tmp_path / "test.sqlite3"
    store = Store(path)
    store.add(sample(), "mqtt", utc_now() - timedelta(hours=25))
    store.add(sample(soil_raw=2400), "mqtt")
    reopened = Store(path)
    assert reopened.latest()["soil_raw"] == 2400
    assert len(reopened.history(24)) == 1


@pytest.mark.parametrize("changes", [
    {"soil_raw": 4096}, {"soil_percent": -1}, {"light_lux": float("nan")},
    {"humidity_percent": 101}, {"device_id": "unexpected"},
])
def test_reject_invalid_readings(changes):
    with pytest.raises(ValidationError):
        sample(**changes)


def test_demo_api_and_control_lock(tmp_path):
    with TestClient(create_app(tmp_path / "demo.sqlite3", mode="demo", demo_interval=3600)) as client:
        latest = client.get("/api/latest").json()
        assert latest["mode"] == "demo"
        assert latest["online"] is True
        assert latest["reading"]["source"] == "demo"
        assert client.get("/api/history").json()["readings"]
        assert client.get("/api/history?hours=0").status_code == 422
        assert client.post("/api/water", json={"duration_ms": 1000}).status_code == 409
        assert client.get("/").status_code == 200
        client.app.state.store.add(sample(), "demo", utc_now() - timedelta(seconds=60))
        assert client.get("/api/latest").json()["stale"] is True
        assert client.get("/api/latest").json()["online"] is False


def test_missing_reading_is_offline(tmp_path):
    with TestClient(create_app(tmp_path / "empty.sqlite3", mode="demo")) as client:
        with client.app.state.store.connect() as db:
            db.execute("DELETE FROM readings")
        data = client.get("/api/latest").json()
        assert data["reading"] is None
        assert data["online"] is False


def test_restart_keeps_history(tmp_path):
    path = tmp_path / "restart.sqlite3"
    with TestClient(create_app(path, mode="demo")) as client:
        before = len(client.get("/api/history").json()["readings"])
    with TestClient(create_app(path, mode="demo")) as client:
        assert len(client.get("/api/history").json()["readings"]) > before


def test_nullable_failed_sensors():
    reading = sample(soil_percent=None, temperature_c=None, errors=["dht11_read_failed"])
    assert reading.temperature_c is None


def test_invalid_mode():
    with pytest.raises(ValueError):
        create_app(mode="typo")


def test_mqtt_ingest_retain_disconnect_and_invalid_payload(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import paho.mqtt.client as mqtt
    import json

    class FakeClient:
        def __init__(self, *args, **kwargs):
            clients.append(self)

        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    clients = []
    monkeypatch.setattr(mqtt, "Client", FakeClient)
    with TestClient(create_app(tmp_path / "mqtt.sqlite3", mode="mqtt")) as api:
        client = clients[0]
        client.on_connect(client, None, None, SimpleNamespace(is_failure=False), None)
        def send(topic, payload, retain=False):
            client.on_message(client, None, SimpleNamespace(
                topic="plant/plant-01/" + topic, payload=payload, retain=retain))
        send("sensor", sample().model_dump_json().encode(), retain=True)
        assert api.get("/api/latest").json()["reading"] is None
        send("status", b"[]")
        send("sensor", b"invalid")
        send("sensor", json.dumps({"device_id": "wrong"}).encode())
        assert api.get("/api/latest").json()["reading"] is None
        send("sensor", sample().model_dump_json().encode())
        assert api.get("/api/latest").json()["online"] is True
        send("status", b'{"online":false}')
        assert api.get("/api/latest").json()["online"] is False
        client.on_disconnect(client, None, None, None, None)
        assert api.get("/api/latest").json()["broker_connected"] is False
