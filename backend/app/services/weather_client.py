import asyncio
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from time import monotonic
from typing import Literal

import httpx

from app.services.aqi_client import CITY_COORDINATES, canonical_city


OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1"
MET_NO_BASE_URL = "https://api.met.no/weatherapi/locationforecast/2.0"
MET_NO_USER_AGENT = "PromptWars/0.1 (github.com/aadarsh-create/prompt-wars)"
TEMPERATURE_CACHE_TTL_SECONDS = 3 * 60 * 60

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TemperatureReading:
    temperature_c: float
    source: Literal["Open-Meteo", "MET Norway"]
    observed_at: str


class WeatherError(Exception):
    pass


_temperature_cache: dict[str, tuple[float, TemperatureReading]] = {}
_city_locks: dict[str, asyncio.Lock] = {}
_cache_lock = Lock()


def _city_lock(city_key: str) -> asyncio.Lock:
    with _cache_lock:
        lock = _city_locks.get(city_key)
        if lock is None:
            lock = asyncio.Lock()
            _city_locks[city_key] = lock
        return lock


def _cached_temperature(city_key: str) -> TemperatureReading | None:
    with _cache_lock:
        cached = _temperature_cache.get(city_key)
        if cached is None:
            return None
        cached_at, reading = cached
        if monotonic() - cached_at >= TEMPERATURE_CACHE_TTL_SECONDS:
            del _temperature_cache[city_key]
            return None
        return reading


def _cache_temperature(city_key: str, reading: TemperatureReading) -> None:
    with _cache_lock:
        _temperature_cache[city_key] = (monotonic(), reading)


def _parse_observed_at(value: object, *, utc_offset_seconds: object = 0) -> str:
    if not isinstance(value, str):
        raise WeatherError("Weather service returned an invalid observation time.")
    try:
        observed_at = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise WeatherError("Weather service returned an invalid observation time.") from error

    if observed_at.tzinfo is None:
        if (
            isinstance(utc_offset_seconds, bool)
            or not isinstance(utc_offset_seconds, int)
        ):
            raise WeatherError("Weather service returned an invalid time zone.")
        observed_at = observed_at.replace(
            tzinfo=timezone(timedelta(seconds=utc_offset_seconds))
        )
    return observed_at.isoformat()


def _temperature_reading(
    temperature: object,
    source: Literal["Open-Meteo", "MET Norway"],
    observed_at: object,
    *,
    utc_offset_seconds: object = 0,
) -> TemperatureReading:
    if (
        isinstance(temperature, bool)
        or not isinstance(temperature, (int, float))
        or not math.isfinite(temperature)
    ):
        raise WeatherError("Weather service returned an invalid temperature.")
    return TemperatureReading(
        temperature_c=float(temperature),
        source=source,
        observed_at=_parse_observed_at(
            observed_at,
            utc_offset_seconds=utc_offset_seconds,
        ),
    )


async def _fetch_open_meteo(
    latitude: float,
    longitude: float,
) -> TemperatureReading:
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
                    "timezone": "UTC",
                },
            )
    except httpx.HTTPError as error:
        raise WeatherError("Unable to reach Open-Meteo.") from error

    if response.is_error:
        raise WeatherError(f"Open-Meteo returned HTTP {response.status_code}.")
    try:
        payload = response.json()
    except ValueError as error:
        raise WeatherError("Open-Meteo returned invalid JSON.") from error

    current = payload.get("current") if isinstance(payload, dict) else None
    utc_offset_seconds = (
        payload.get("utc_offset_seconds") if isinstance(payload, dict) else 0
    )
    return _temperature_reading(
        current.get("temperature_2m") if isinstance(current, dict) else None,
        "Open-Meteo",
        current.get("time") if isinstance(current, dict) else None,
        utc_offset_seconds=utc_offset_seconds,
    )


async def _fetch_met_no(
    latitude: float,
    longitude: float,
) -> TemperatureReading:
    try:
        async with httpx.AsyncClient(
            base_url=MET_NO_BASE_URL,
            headers={"User-Agent": MET_NO_USER_AGENT},
            timeout=httpx.Timeout(10.0),
        ) as client:
            response = await client.get(
                "/compact",
                params={
                    "lat": f"{latitude:.4f}",
                    "lon": f"{longitude:.4f}",
                },
            )
    except httpx.HTTPError as error:
        raise WeatherError("Unable to reach MET Norway.") from error

    if response.is_error:
        raise WeatherError(f"MET Norway returned HTTP {response.status_code}.")
    try:
        payload = response.json()
    except ValueError as error:
        raise WeatherError("MET Norway returned invalid JSON.") from error

    properties = payload.get("properties") if isinstance(payload, dict) else None
    timeseries = properties.get("timeseries") if isinstance(properties, dict) else None
    if not isinstance(timeseries, list):
        raise WeatherError("MET Norway returned an invalid forecast.")

    now = datetime.now(timezone.utc)
    readings: list[tuple[float, TemperatureReading]] = []
    for item in timeseries:
        if not isinstance(item, dict):
            continue
        data = item.get("data")
        instant = data.get("instant") if isinstance(data, dict) else None
        details = instant.get("details") if isinstance(instant, dict) else None
        try:
            reading = _temperature_reading(
                details.get("air_temperature") if isinstance(details, dict) else None,
                "MET Norway",
                item.get("time"),
            )
            observed_at = datetime.fromisoformat(
                reading.observed_at.replace("Z", "+00:00")
            )
        except (ValueError, WeatherError):
            continue
        readings.append((abs((observed_at - now).total_seconds()), reading))

    if not readings:
        raise WeatherError("MET Norway returned no valid temperature forecast.")
    return min(readings, key=lambda item: item[0])[1]


async def fetch_city_temperature(city: str) -> TemperatureReading:
    normalized_city = canonical_city(city)
    city_key = normalized_city.casefold()
    _, latitude, longitude = CITY_COORDINATES[city_key]

    async with _city_lock(city_key):
        cached = _cached_temperature(city_key)
        if cached is not None:
            return cached

        try:
            reading = await _fetch_open_meteo(latitude, longitude)
        except WeatherError as open_meteo_error:
            logger.warning(
                "Open-Meteo lookup failed for %s; trying MET Norway: %s",
                normalized_city,
                open_meteo_error,
            )
            try:
                reading = await _fetch_met_no(latitude, longitude)
            except WeatherError as met_no_error:
                raise WeatherError(
                    f"Open-Meteo failed ({open_meteo_error}); "
                    f"MET Norway failed ({met_no_error})."
                ) from met_no_error

        _cache_temperature(city_key, reading)
        return reading
