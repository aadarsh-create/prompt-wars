import asyncio
from datetime import datetime, timezone

import httpx
import pytest

from app.services import weather_client


@pytest.fixture(autouse=True)
def clear_weather_cache():
    with weather_client._cache_lock:
        weather_client._temperature_cache.clear()
        weather_client._city_locks.clear()


def patch_weather_transport(monkeypatch, handler):
    original_async_client = weather_client.httpx.AsyncClient
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        weather_client.httpx,
        "AsyncClient",
        lambda **kwargs: original_async_client(transport=transport, **kwargs),
    )


def test_fetch_city_temperature_uses_open_meteo_celsius_and_city_coordinates(monkeypatch):
    observed_request = {}

    def handle(request):
        observed_request["url"] = request.url
        return httpx.Response(
            200,
            json={
                "utc_offset_seconds": 0,
                "current": {
                    "temperature_2m": 23.75,
                    "time": "2026-11-28T13:00:00",
                },
            },
            request=request,
        )

    patch_weather_transport(monkeypatch, handle)
    reading = asyncio.run(weather_client.fetch_city_temperature("Hyderabad"))

    assert reading.temperature_c == 23.75
    assert reading.source == "Open-Meteo"
    assert reading.observed_at == "2026-11-28T13:00:00+00:00"
    assert observed_request["url"].path == "/v1/forecast"
    assert observed_request["url"].params["temperature_unit"] == "celsius"
    assert observed_request["url"].params["latitude"] == "17.385"
    assert observed_request["url"].params["longitude"] == "78.4867"
    assert observed_request["url"].params["timezone"] == "UTC"


def test_fetch_city_temperature_falls_back_to_met_no_and_caches_result(monkeypatch):
    observed_requests = {"open_meteo": 0, "met_no": 0}
    observed_met_request = {}
    forecast_time = datetime.now(timezone.utc).isoformat()

    def handle(request):
        if request.url.host == "api.open-meteo.com":
            observed_requests["open_meteo"] += 1
            return httpx.Response(429, request=request)
        observed_requests["met_no"] += 1
        observed_met_request["request"] = request
        return httpx.Response(
            200,
            json={
                "properties": {
                    "timeseries": [
                        {
                            "time": forecast_time,
                            "data": {
                                "instant": {
                                    "details": {"air_temperature": 19.25},
                                },
                            },
                        },
                    ],
                },
            },
            request=request,
        )

    patch_weather_transport(monkeypatch, handle)

    async def read_temperature_concurrently():
        return await asyncio.gather(
            weather_client.fetch_city_temperature("Hyderabad"),
            weather_client.fetch_city_temperature("Hyderabad"),
        )

    first, second = asyncio.run(read_temperature_concurrently())

    assert first == second
    assert first.temperature_c == 19.25
    assert first.source == "MET Norway"
    assert first.observed_at == forecast_time
    assert observed_requests == {"open_meteo": 1, "met_no": 1}
    request = observed_met_request["request"]
    assert request.url.path.endswith("/compact")
    assert request.url.params["lat"] == "17.3850"
    assert request.url.params["lon"] == "78.4867"
    assert request.headers["user-agent"] == weather_client.MET_NO_USER_AGENT
