import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import aqi_cache
from app.services import aqi_client
from app.services.weather_client import TemperatureReading, WeatherError


@pytest.fixture(autouse=True)
def clear_aqi_cache():
    with aqi_cache._lock:
        aqi_cache._cache.clear()


@pytest.fixture
def openaq_response(monkeypatch) -> dict:
    now = datetime.now(timezone.utc)
    observed = now - timedelta(hours=1)
    observed_text = observed.isoformat().replace("+00:00", "Z")
    observed_iso = observed.isoformat()

    locations_payload = {
        "results": [
            {
                "id": 42,
                "name": "Delhi test station",
                "distance": 1200,
                "coordinates": {"latitude": 28.6139, "longitude": 77.2090},
                "datetimeLast": {"utc": observed_text},
                "sensors": [
                    {"id": 101, "parameter": {"name": "pm25", "units": "µg/m³"}},
                    {"id": 102, "parameter": {"name": "pm10", "units": "µg/m³"}},
                ],
            }
        ]
    }
    latest_payload = {
        "results": [
            {
                "sensorsId": 101,
                "value": 75,
                "datetime": {"utc": observed_text},
            },
            {
                "sensorsId": 102,
                "value": 180,
                "datetime": {"utc": observed_text},
            },
        ]
    }
    history_timestamps = [
        now - timedelta(hours=3),
        now - timedelta(hours=2),
    ]
    hourly_payloads = {
        "/sensors/101/hours": {
            "results": [
                {
                    "value": value,
                    "period": {"datetimeTo": {"utc": timestamp.isoformat()}},
                }
                for timestamp, value in zip(history_timestamps, (30, 60))
            ]
        },
        "/sensors/102/hours": {
            "results": [
                {
                    "value": value,
                    "period": {"datetimeTo": {"utc": timestamp.isoformat()}},
                }
                for timestamp, value in zip(history_timestamps, (50, 100))
            ]
        },
    }

    async def mock_get_json(client, path, *, params=None):
        if path == "/locations":
            return locations_payload
        if path == "/locations/42/latest":
            return latest_payload
        if path in hourly_payloads:
            assert params is not None
            assert "datetime_from" in params
            assert "datetime_to" in params
            assert "date_from" not in params
            assert "date_to" not in params
            return hourly_payloads[path]
        raise aqi_client.OpenAQError(f"Unexpected path: {path}")

    monkeypatch.setenv("OPENAQ_API_KEY", "test-key")
    monkeypatch.setattr(aqi_client, "_get_json", mock_get_json)
    return {
        "observed_text": observed_iso,
        "history_timestamps": [timestamp.isoformat() for timestamp in history_timestamps],
    }


def test_parses_openaq_location_and_calculates_aqi(openaq_response):
    reading = asyncio.run(aqi_client.fetch_city_reading("Delhi"))

    assert reading["city"] == "Delhi"
    assert reading["pm25"] == 75
    assert reading["pm10"] == 180
    assert reading["aqi"] == 153
    assert reading["category"] == "Moderate"
    assert reading["observed_at"] == openaq_response["observed_text"]
    assert reading["source"] == "OpenAQ"
    assert reading["is_stale"] is False
    assert reading["history_parameter"] == "both"
    assert reading["history"] == [
        {"timestamp": openaq_response["history_timestamps"][0], "aqi": 50},
        {"timestamp": openaq_response["history_timestamps"][1], "aqi": 100},
    ]


def test_uses_available_pollutant_history_when_other_sensor_fails(
    openaq_response,
    monkeypatch,
):
    original_get_json = aqi_client._get_json

    async def fail_pm10_history(client, path, *, params=None):
        if path == "/sensors/102/hours":
            raise aqi_client.OpenAQError("PM10 history unavailable")
        return await original_get_json(client, path, params=params)

    monkeypatch.setattr(aqi_client, "_get_json", fail_pm10_history)
    reading = asyncio.run(aqi_client.fetch_city_reading("Delhi"))

    assert reading["history_parameter"] == "pm25"
    assert reading["history"] == [
        {"timestamp": openaq_response["history_timestamps"][0], "aqi": 50},
        {"timestamp": openaq_response["history_timestamps"][1], "aqi": 100},
    ]


def test_history_failure_does_not_block_current_reading(openaq_response, monkeypatch):
    original_get_json = aqi_client._get_json

    async def fail_history(client, path, *, params=None):
        if path.startswith("/sensors/"):
            raise aqi_client.OpenAQError("history unavailable")
        return await original_get_json(client, path, params=params)

    monkeypatch.setattr(aqi_client, "_get_json", fail_history)
    reading = asyncio.run(aqi_client.fetch_city_reading("Delhi"))

    assert reading["aqi"] == 153
    assert reading["history"] == []


def test_pm25_sub_index_uses_cpcb_boundaries():
    assert aqi_client._sub_index("pm25", 30) == 50
    assert aqi_client._sub_index("pm25", 60) == 100
    assert aqi_client._sub_index("pm25", 90) == 200


def test_category_boundaries():
    assert aqi_client._aqi_category(50) == "Good"
    assert aqi_client._aqi_category(51) == "Satisfactory"
    assert aqi_client._aqi_category(200) == "Moderate"
    assert aqi_client._aqi_category(301) == "Very Poor"
    assert aqi_client._aqi_category(500) == "Severe"


def test_returns_stale_cached_reading_when_provider_fails(monkeypatch):
    cached = {
        "city": "Delhi",
        "aqi": 143,
        "category": "Moderate",
        "pm25": 91,
        "pm10": 180,
        "observed_at": "2026-11-26T10:00:00+00:00",
        "source": "OpenAQ",
        "is_stale": False,
    }
    aqi_cache.cache_reading("Delhi", cached)

    async def provider_failure(city):
        raise aqi_client.OpenAQError("provider unavailable")

    async def temperature_available(city):
        return TemperatureReading(
            temperature_c=21.5,
            source="Open-Meteo",
            observed_at="2026-11-28T12:00:00+00:00",
        )

    monkeypatch.setattr("app.routers.aqi.fetch_city_reading", provider_failure)
    monkeypatch.setattr("app.routers.aqi.fetch_city_temperature", temperature_available)

    with TestClient(app) as client:
        response = client.get("/api/aqi", params={"city": "delhi"})

    assert response.status_code == 200
    assert response.json()["is_stale"] is True
    assert response.json()["aqi"] == 143
    assert response.json()["temperature_c"] == 21.5
    assert response.json()["temperature_source"] == "Open-Meteo"


def test_returns_503_when_provider_and_cache_are_unavailable(monkeypatch):
    async def provider_failure(city):
        raise aqi_client.OpenAQError("provider unavailable")

    async def temperature_failure(city):
        raise WeatherError("weather unavailable")

    monkeypatch.setattr("app.routers.aqi.fetch_city_reading", provider_failure)
    monkeypatch.setattr("app.routers.aqi.fetch_city_temperature", temperature_failure)

    with TestClient(app) as client:
        response = client.get("/api/aqi", params={"city": "Mumbai"})

    assert response.status_code == 503
    assert "no cached reading" in response.json()["detail"]


def test_aqi_response_includes_temperature_when_available(openaq_response, monkeypatch):
    async def temperature_available(city):
        return TemperatureReading(
            temperature_c=24.5,
            source="MET Norway",
            observed_at="2026-11-28T12:00:00+00:00",
        )

    monkeypatch.setattr("app.routers.aqi.fetch_city_temperature", temperature_available)

    with TestClient(app) as client:
        response = client.get("/api/aqi", params={"city": "Delhi"})

    assert response.status_code == 200
    assert response.json()["temperature_c"] == 24.5
    assert response.json()["temperature_source"] == "MET Norway"
    assert response.json()["temperature_observed_at"] == "2026-11-28T12:00:00+00:00"


def test_rejects_unsupported_city():
    with TestClient(app) as client:
        response = client.get("/api/aqi", params={"city": "London"})

    assert response.status_code == 422