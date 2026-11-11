import asyncio
import json
import logging
import math
import os
import sqlite3
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, model_validator

ROOT = Path(__file__).resolve().parent.parent
log = logging.getLogger(__name__)


class Reading(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    device_id: str = Field(pattern=r"^plant-01$")
    soil_raw: int = Field(ge=0, le=4095)
    soil_percent: float | None = Field(default=None, ge=0, le=100)
    temperature_c: float | None = Field(default=None, ge=-20, le=60)
    humidity_percent: float | None = Field(default=None, ge=0, le=100)
    light_lux: float | None = Field(default=None, ge=0, le=120000)
    errors: list[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def check_errors(self):
        if any(len(item) > 80 for item in self.errors):
            raise ValueError("error descriptions must be at most 80 characters")
        return self


def utc_now():
    return datetime.now(timezone.utc)


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY, received_at TEXT NOT NULL,
                source TEXT NOT NULL, payload TEXT NOT NULL)""")
            db.execute("CREATE INDEX IF NOT EXISTS readings_time ON readings(received_at)")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        try:
            with db:
                yield db
        finally:
            db.close()

    def add(self, reading, source, received_at=None):
        record = {**reading.model_dump(), "source": source,
                  "received_at": (received_at or utc_now()).isoformat()}
        with self.connect() as db:
            db.execute("INSERT INTO readings(received_at, source, payload) VALUES (?, ?, ?)",
                       (record["received_at"], source, json.dumps(record)))
        return record

    def latest(self):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM readings ORDER BY id DESC LIMIT 1").fetchone()
        return json.loads(row[0]) if row else None

    def history(self, hours):
        cutoff = (utc_now() - timedelta(hours=hours)).isoformat()
        with self.connect() as db:
            rows = db.execute(
                "SELECT payload FROM readings WHERE received_at >= ? ORDER BY id DESC LIMIT 10000",
                (cutoff,)).fetchall()
        return [json.loads(row[0]) for row in reversed(rows)]


def create_app(db_path=None, mode=None, demo_interval=10):
    mode = mode or os.environ.get("PLANT_MODE", "demo")
    if mode not in ("demo", "mqtt"):
        raise ValueError("PLANT_MODE must be demo or mqtt")

    async def simulate(store):
        step = 0
        while True:
            wave = math.sin(step / 12)
            store.add(Reading(device_id="plant-01", soil_raw=int(2300 + wave * 400),
                              soil_percent=round(48 - wave * 15, 1),
                              temperature_c=round(24 + wave, 1),
                              humidity_percent=round(62 - wave * 5, 1),
                              light_lux=round(650 + wave * 150, 1)), "demo")
            step += 1
            await asyncio.sleep(demo_interval)

    @asynccontextmanager
    async def lifespan(app):
        app.state.store = Store(db_path or os.environ.get("PLANT_DB", ROOT / "data" / f"{mode}.sqlite3"))
        app.state.device_online = None
        app.state.broker_connected = False
        client = None
        task = None
        if mode == "demo":
            task = asyncio.create_task(simulate(app.state.store))
        else:
            import paho.mqtt.client as mqtt

            def on_connect(client, userdata, flags, reason_code, properties):
                app.state.broker_connected = not reason_code.is_failure
                if not reason_code.is_failure:
                    client.subscribe([("plant/plant-01/sensor", 0), ("plant/plant-01/status", 1)])

            def on_disconnect(client, userdata, flags, reason_code, properties):
                app.state.broker_connected = False
                app.state.device_online = None

            def on_message(client, userdata, message):
                try:
                    # Retained sensor samples could make stale data look fresh.
                    if message.topic.endswith("/sensor") and not message.retain:
                        app.state.store.add(Reading.model_validate_json(message.payload), "mqtt")
                        app.state.device_online = True
                    elif message.topic.endswith("/status"):
                        status = json.loads(message.payload)
                        if not isinstance(status, dict):
                            raise ValueError("status must be an object")
                        if type(status.get("online")) is not bool:
                            raise ValueError("online must be a boolean")
                        app.state.device_online = status["online"]
                except (ValueError, TypeError, sqlite3.Error):
                    log.warning("Rejected invalid MQTT message on %s", message.topic)

            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="plant-gateway")
            client.on_connect = on_connect
            client.on_disconnect = on_disconnect
            client.on_message = on_message
            username = os.environ.get("MQTT_USERNAME")
            if username:
                client.username_pw_set(username, os.environ.get("MQTT_PASSWORD"))
            client.reconnect_delay_set(min_delay=1, max_delay=30)
            client.connect_async(os.environ.get("MQTT_HOST", "127.0.0.1"),
                                 int(os.environ.get("MQTT_PORT", "1883")), keepalive=30)
            client.loop_start()
        try:
            yield
        finally:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            if client:
                client.disconnect()
                client.loop_stop()

    app = FastAPI(title="Plant Care Gateway", lifespan=lifespan)

    @app.get("/api/latest")
    def latest():
        reading = app.state.store.latest()
        age = (utc_now() - datetime.fromisoformat(reading["received_at"])).total_seconds() if reading else None
        fresh = age is not None and age < 45
        online = fresh if mode == "demo" else (fresh and app.state.broker_connected and app.state.device_online is True)
        return {"mode": mode, "online": bool(online), "stale": not fresh,
                "broker_connected": app.state.broker_connected, "reading": reading}

    @app.get("/api/history")
    def history(hours: int = Query(default=24, ge=1, le=168)):
        return {"hours": hours, "readings": app.state.store.history(hours)}

    @app.post("/api/water")
    def water():
        raise HTTPException(status_code=409, detail="Pump control is locked pending hardware acceptance")

    app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(ROOT / "web" / "index.html")

    return app


app = create_app()
