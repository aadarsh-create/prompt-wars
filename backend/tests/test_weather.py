import asyncio

import httpx

from app.services import weather_client


def test_fetch_city_temperature_uses_celsius_for_city_coordinates(monkeypatch):
    observed_request = {}

    def handle(request):
        observed_request["url"] = request.url
        return httpx.Response(
            200,
            json={"current": {"temperature_2m": 23.75}},
            request=request,
        )

    original_async_client = weather_client.httpx.AsyncClient
    transport = httpx.MockTransport(handle)
    monkeypatch.setattr(
        weather_client.httpx,
        "AsyncClient",
        lambda **kwargs: original_async_client(transport=transport, **kwargs),
    )

    temperature = asyncio.run(weather_client.fetch_city_temperature("Hyderabad"))

    assert temperature == 23.75
    assert observed_request["url"].path == "/v1/forecast"
    assert observed_request["url"].params["temperature_unit"] == "celsius"
    assert observed_request["url"].params["latitude"] == "17.385"
    assert observed_request["url"].params["longitude"] == "78.4867"
