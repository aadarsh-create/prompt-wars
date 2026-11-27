import math

import httpx

from app.services.aqi_client import CITY_COORDINATES, canonical_city


OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1"


class WeatherError(Exception):
    pass


async def fetch_city_temperature(city: str) -> float:
    normalized_city = canonical_city(city)
    _, latitude, longitude = CITY_COORDINATES[normalized_city.casefold()]

    try:
        async with httpx.AsyncClient(
            base_url=OPEN_METEO_BASE_URL,
            timeout=httpx.Timeout(10.0),
        ) as client:
            response = await client.get(
                "/forecast",
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "current": "temperature_2m",
                    "temperature_unit": "celsius",
                    "timezone": "auto",
                },
            )
    except httpx.HTTPError as error:
        raise WeatherError("Unable to reach the weather service.") from error

    if response.is_error:
        raise WeatherError(f"Weather service returned HTTP {response.status_code}.")
    try:
        payload = response.json()
    except ValueError as error:
        raise WeatherError("Weather service returned invalid JSON.") from error

    current = payload.get("current") if isinstance(payload, dict) else None
    temperature = current.get("temperature_2m") if isinstance(current, dict) else None
    if (
        isinstance(temperature, bool)
        or not isinstance(temperature, (int, float))
        or not math.isfinite(temperature)
    ):
        raise WeatherError("Weather service returned an invalid temperature.")
    return float(temperature)
