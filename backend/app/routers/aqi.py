import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.services.aqi_cache import cache_reading, get_cached_reading
from app.services.aqi_client import OpenAQError, canonical_city, fetch_city_reading


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/aqi")
async def get_aqi(
    city: str = Query(..., description="One of the supported Indian cities"),
) -> dict[str, Any]:
    try:
        normalized_city = canonical_city(city)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail="Unsupported city. Choose Delhi, Mumbai, Kolkata, Chennai, Bengaluru, or Hyderabad.",
        ) from error

    try:
        reading = await fetch_city_reading(normalized_city)
    except OpenAQError as error:
        logger.warning("AQI lookup failed for %s: %s", normalized_city, error)
        cached_reading = get_cached_reading(normalized_city)
        if cached_reading is not None:
            cached_reading["is_stale"] = True
            return cached_reading
        raise HTTPException(
            status_code=503,
            detail="Air-quality data is unavailable and no cached reading exists.",
        ) from error

    cache_reading(normalized_city, reading)
    return reading