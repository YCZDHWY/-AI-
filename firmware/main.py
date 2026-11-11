"""Read-only telemetry for a verified classic ESP32 pinout. No relay output."""
import json
import time
import machine
import network
import dht
from umqtt.simple import MQTTClient
import config

DEVICE = "plant-01"
TOPIC = "plant/" + DEVICE
adc = machine.ADC(machine.Pin(config.SOIL_PIN))
adc.atten(machine.ADC.ATTN_11DB)
adc.width(machine.ADC.WIDTH_12BIT)
temperature = dht.DHT11(machine.Pin(config.DHT_PIN))
i2c = machine.SoftI2C(sda=machine.Pin(config.I2C_SDA),
                       scl=machine.Pin(config.I2C_SCL), freq=100000)
wifi = network.WLAN(network.STA_IF)
wifi.active(True)


def read_sensors():
    raw = sum(adc.read() for _ in range(8)) // 8
    data = {"device_id": DEVICE, "soil_raw": raw, "soil_percent": None,
            "temperature_c": None, "humidity_percent": None,
            "light_lux": None, "errors": []}
    dry, wet = config.SOIL_DRY, config.SOIL_WET
    if dry is not None and wet is not None and dry != wet:
        data["soil_percent"] = round(max(0, min(100, (raw - dry) * 100 / (wet - dry))), 1)
    if raw <= 5 or raw >= 4090:
        data["errors"].append("soil_adc_out_of_range")
        data["soil_percent"] = None
    try:
        temperature.measure()
        data["temperature_c"] = temperature.temperature()
        data["humidity_percent"] = temperature.humidity()
    except OSError:
        data["errors"].append("dht11_read_failed")
    try:
        i2c.writeto(0x23, bytes([0x20]))
        time.sleep_ms(180)
        light = i2c.readfrom(0x23, 2)
        data["light_lux"] = round((light[0] * 256 + light[1]) / 1.2, 1)
    except OSError:
        data["errors"].append("bh1750_read_failed")
    return data


while True:
    client = None
    try:
        if not wifi.isconnected():
            wifi.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
            deadline = time.ticks_add(time.ticks_ms(), 20000)
            while not wifi.isconnected():
                if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                    raise OSError("WiFi timeout")
                time.sleep_ms(200)
        client = MQTTClient(DEVICE, config.MQTT_HOST, port=config.MQTT_PORT,
                            user=config.MQTT_USERNAME or None,
                            password=config.MQTT_PASSWORD or None, keepalive=30)
        client.set_last_will((TOPIC + "/status").encode(), b'{"online":false}', retain=True)
        client.connect()
        client.publish((TOPIC + "/status").encode(), b'{"online":true}', retain=True)
        while wifi.isconnected():
            reading = read_sensors()
            print(reading)
            client.publish((TOPIC + "/sensor").encode(), json.dumps(reading).encode(), retain=False)
            time.sleep(10)
    except (OSError, ValueError) as error:
        print("Telemetry reconnect:", error)
    finally:
        if client is not None:
            # Close without DISCONNECT so the broker emits the offline will.
            try:
                client.sock.close()
            except (OSError, AttributeError):
                pass
    time.sleep(5)
