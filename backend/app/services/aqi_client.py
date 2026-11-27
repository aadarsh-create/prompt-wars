import asyncio
import logging
import math
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx


OPENAQ_BASE_URL = "https://api.openaq.org/v3"
SEARCH_RADIUS_METERS = 10_000
READING_MAX_AGE = timedelta(hours=48)
HISTORY_PERIOD = timedelta(hours=24)
CITY_COORDINATES = {
    "delhi": ("Delhi", 28.6139, 77.2090),
    "mumbai": ("Mumbai", 19.0760, 72.8777),
    "kolkata": ("Kolkata", 22.5726, 88.3639),
    "chennai": ("Chennai", 13.0827, 80.2707),
    "bengaluru": ("Bengaluru", 12.9716, 77.5946),
    "hyderabad": ("Hyderabad", 17.3850, 78.4867),
}
logger = logging.getLogger(__name__)

AQI_BREAKPOINTS = {
    "pm25": (
        (0, 30, 0, 50),
        (31, 60, 51, 100),
        (61, 90, 101, 200),
        (91, 120, 201, 300),
        (121, 250, 301, 400),
        (251, math.inf, 401, 500),
    ),
    "pm10": (
        (0, 50, 0, 50),
        (51, 100, 51, 100),
        (101, 250, 101, 200),
        (251, 350, 201, 300),
        (351, 430, 301, 400),
        (431, math.inf, 401, 500),
    ),
}

AQI_CATEGORIES = (
    (50, "Good"),
    (100, "Satisfactory"),
    (200, "Moderate"),
    (300, "Poor"),
    (400, "Very Poor"),
    (500, "Severe"),
)


class OpenAQError(Exception):
    pass


def canonical_city(city: str) -> str:
    city_details = CITY_COORDINATES.get(city.strip().casefold())
    if city_details is None:
        raise ValueError(f"Unsupported city: {city}")
    return city_details[0]


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _distance_meters(location: dict[str, Any], latitude: float, longitude: float) -> float:
    distance = location.get("distance")
    if isinstance(distance, (int, float)) and math.isfinite(distance):
        return float(distance)

    coordinates = location.get("coordinates")
    if not isinstance(coordinates, dict):
        return math.inf
    station_latitude = coordinates.get("latitude")
    station_longitude = coordinates.get("longitude")
    if not isinstance(station_latitude, (int, float)) or not isinstance(
        station_longitude, (int, float)
    ):
        return math.inf

    earth_radius_meters = 6_371_000
    lat1 = math.radians(latitude)
    lat2 = math.radians(station_latitude)
    lat_delta = math.radians(station_latitude - latitude)
    lon_delta = math.radians(station_longitude - longitude)
    haversine = (
        math.sin(lat_delta / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(lon_delta / 2) ** 2
    )
    return earth_radius_meters * 2 * math.atan2(
        math.sqrt(haversine), math.sqrt(1 - haversine)
    )


def _sub_index(parameter: str, concentration: float) -> int:
    concentration = math.floor(concentration + 0.5)
    for lower, upper, index_lower, index_upper in AQI_BREAKPOINTS[parameter]:
        if lower <= concentration <= upper:
            if math.isinf(upper):
                return 500
            sub_index = (
                (index_upper - index_lower)
                * (concentration - lower)
                / (upper - lower)
                + index_lower
            )
            return min(500, math.floor(sub_index + 0.5))
    return 500


def _location_last_seen(location: dict[str, Any]) -> datetime | None:
    datetime_last = location.get("datetimeLast")
    if not isinstance(datetime_last, dict):
        return None
    return _parse_datetime(datetime_last.get("utc"))


def _aqi_category(aqi: int) -> str:
    for upper_bound, category in AQI_CATEGORIES:
        if aqi <= upper_bound:
            return category
    return "Severe"


def _sensor_parameters(location: dict[str, Any]) -> dict[str, str]:
    sensors = location.get("sensors")
    if not isinstance(sensors, list):
        return {}

    parameters: dict[str, str] = {}
    for sensor in sensors:
        if not isinstance(sensor, dict):
            continue
        sensor_id = sensor.get("id")
        parameter = sensor.get("parameter")
        if not isinstance(parameter, dict):
            continue
        parameter_name = parameter.get("name")
        units = parameter.get("units")
        normalized_units = (
            units.lower()
            .replace("μ", "u")
            .replace("µ", "u")
            .replace("³", "3")
            .replace(" ", "")
            if isinstance(units, str)
            else ""
        )
        if (
            sensor_id is not None
            and parameter_name in ("pm25", "pm10")
            and normalized_units == "ug/m3"
        ):
            parameters[str(sensor_id)] = parameter_name
    return parameters


def _latest_pm_readings(
    payload: dict[str, Any],
    sensor_parameters: dict[str, str],
    now: datetime,
) -> dict[str, tuple[float, datetime]]:
    results = payload.get("results")
    if not isinstance(results, list):
        raise OpenAQError("OpenAQ returned an invalid latest-measurements payload.")

    latest: dict[str, tuple[float, datetime]] = {}
    cutoff = now - READING_MAX_AGE
    for result in results:
        if not isinstance(result, dict):
            continue
        parameter = sensor_parameters.get(str(result.get("sensorsId")))
        if parameter not in ("pm25", "pm10"):
            continue
        value = result.get("value")
        datetime_payload = result.get("datetime")
        timestamp = (
            _parse_datetime(datetime_payload.get("utc"))
            if isinstance(datetime_payload, dict)
            else None
        )
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
            or timestamp is None
            or timestamp < cutoff
            or timestamp > now + timedelta(minutes=5)
        ):
            continue
        previous = latest.get(parameter)
        if previous is None or timestamp > previous[1]:
            latest[parameter] = (float(value), timestamp)
    return latest


def _hourly_pm_readings(
    payload: dict[str, Any],
    now: datetime,
) -> dict[datetime, float]:
    results = payload.get("results")
    if not isinstance(results, list):
        raise OpenAQError("OpenAQ returned an invalid hourly-measurements payload.")

    readings: dict[datetime, float] = {}
    cutoff = now - HISTORY_PERIOD
    for result in results:
        if not isinstance(result, dict):
            continue
        value = result.get("value")
        period = result.get("period")
        datetime_to = period.get("datetimeTo") if isinstance(period, dict) else None
        timestamp = (
            _parse_datetime(datetime_to.get("utc"))
            if isinstance(datetime_to, dict)
            else None
        )
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
            or timestamp is None
            or timestamp < cutoff
            or timestamp > now + timedelta(minutes=5)
        ):
            continue
        readings[timestamp] = float(value)
    return readings


async def _get_json(
    client: httpx.AsyncClient,
    path: str,
    *,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        response = await client.get(path, params=params)
    except httpx.HTTPError as error:
        raise OpenAQError("Unable to reach the OpenAQ API.") from error
    if response.is_error:
        raise OpenAQError(f"OpenAQ API returned HTTP {response.status_code}.")
    try:
        payload = response.json()
    except ValueError as error:
        raise OpenAQError("OpenAQ returned invalid JSON.") from error
    if not isinstance(payload, dict):
        raise OpenAQError("OpenAQ returned an invalid response.")
    return payload


async def fetch_city_reading(city: str) -> dict[str, Any]:
    normalized_city = canonical_city(city)
    city_key = normalized_city.casefold()
    _, latitude, longitude = CITY_COORDINATES[city_key]
    api_key = os.getenv("OPENAQ_API_KEY")
    if not api_key:
        raise OpenAQError("OPENAQ_API_KEY is not configured.")

    headers = {"X-API-Key": api_key}
    timeout = httpx.Timeout(15.0)
    now = datetime.now(timezone.utc)
    try:
        async with httpx.AsyncClient(
            base_url=OPENAQ_BASE_URL,
            headers=headers,
            timeout=timeout,
        ) as client:
            locations_payload = await _get_json(
                client,
                "/locations",
                params={
                    "country": "IN",
                    "coordinates": f"{latitude},{longitude}",
                    "radius": SEARCH_RADIUS_METERS,
                    "limit": 100,
                },
            )
            locations = locations_payload.get("results")
            if not isinstance(locations, list):
                raise OpenAQError("OpenAQ returned an invalid locations payload.")

            cutoff = now - READING_MAX_AGE
            candidates = [
                location
                for location in locations
                if isinstance(location, dict)
                and location.get("id") is not None
                and (
                    (last_seen := _location_last_seen(location)) is not None
                    and cutoff <= last_seen <= now + timedelta(minutes=5)
                )
                and {"pm25", "pm10"}.issubset(set(_sensor_parameters(location).values()))
            ]
            candidates.sort(
                key=lambda location: _distance_meters(location, latitude, longitude)
            )
            if not candidates:
                raise OpenAQError(
                    f"No nearby station has recent PM2.5 and PM10 sensors for {normalized_city}."
                )

            station_errors: list[OpenAQError] = []
            for location in candidates:
                try:
                    latest_payload = await _get_json(
                        client,
                        f"/locations/{location['id']}/latest",
                        params={"limit": 100},
                    )
                    readings = _latest_pm_readings(
                        latest_payload,
                        _sensor_parameters(location),
                        now,
                    )
                except OpenAQError as error:
                    station_errors.append(error)
                    continue
                if "pm25" not in readings or "pm10" not in readings:
                    continue

                pm25, pm25_timestamp = readings["pm25"]
                pm10, pm10_timestamp = readings["pm10"]
                aqi = max(_sub_index("pm25", pm25), _sub_index("pm10", pm10))
                observed_at = min(pm25_timestamp, pm10_timestamp)
                history: list[dict[str, Any]] = []
                try:
                    hourly_by_parameter: dict[str, dict[datetime, float]] = {}
                    history_sensors = [
                        (sensor_id, parameter)
                        for sensor_id, parameter in _sensor_parameters(location).items()
                        if parameter in ("pm25", "pm10")
                    ]
                    hourly_payloads = await asyncio.gather(
                        *(
                            _get_json(
                                client,
                                f"/sensors/{sensor_id}/hours",
                                params={
                                    "datetime_from": (now - HISTORY_PERIOD).isoformat(),
                                    "datetime_to": now.isoformat(),
                                    "limit": 1000,
                                },
                            )
                            for sensor_id, _ in history_sensors
                        )
                    )
                    for (_, parameter), hourly_payload in zip(
                        history_sensors,
                        hourly_payloads,
                    ):
                        hourly_by_parameter[parameter] = _hourly_pm_readings(
                            hourly_payload,
                            now,
                        )
                    common_timestamps = sorted(
                        set(hourly_by_parameter.get("pm25", {}))
                        & set(hourly_by_parameter.get("pm10", {}))
                    )
                    history = [
                        {
                            "timestamp": timestamp.isoformat(),
                            "aqi": max(
                                _sub_index("pm25", hourly_by_parameter["pm25"][timestamp]),
                                _sub_index("pm10", hourly_by_parameter["pm10"][timestamp]),
                            ),
                        }
                        for timestamp in common_timestamps
                    ]
                except OpenAQError as error:
                    logger.warning(
                        "Unable to retrieve 24-hour AQI history for %s: %s",
                        normalized_city,
                        error,
                    )
                return {
                    "city": normalized_city,
                    "aqi": aqi,
                    "category": _aqi_category(aqi),
                    "pm25": pm25,
                    "pm10": pm10,
                    "pm25_observed_at": pm25_timestamp.isoformat(),
                    "pm10_observed_at": pm10_timestamp.isoformat(),
                    "observed_at": observed_at.isoformat(),
                    "source": "OpenAQ",
                    "station": location.get("name") or f"OpenAQ location {location['id']}",
                    "is_stale": False,
                    "history": history,
                }
    except OpenAQError:
        raise

    if station_errors:
        raise OpenAQError(
            f"Unable to retrieve recent PM2.5 and PM10 readings for {normalized_city}."
        ) from station_errors[-1]
    raise OpenAQError(
        f"No nearby station has fresh PM2.5 and PM10 measurements for {normalized_city}."
    )