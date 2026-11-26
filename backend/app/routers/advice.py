import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.rate_limit import limiter
from app.schemas import AdviceRequest, AdviceResponse
from app.services.advice import AdviceServiceError, generate_advice
from app.services.aqi_cache import cache_reading, get_cached_reading
from app.services.aqi_client import OpenAQError, canonical_city, fetch_city_reading


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/advice", response_model=AdviceResponse)
@limiter.limit("10/minute")
async def get_advice(
    request: Request,
    payload: AdviceRequest,
) -> dict[str, Any]:
    city = payload.profile.city.value
    try:
        normalized_city = canonical_city(city)
    except ValueError as error:
        raise HTTPException(status_code=422, detail="Unsupported city.") from error

    try:
        reading = await fetch_city_reading(normalized_city)
        cache_reading(normalized_city, reading)
    except OpenAQError as error:
        logger.warning("AQI lookup failed for advice request in %s: %s", normalized_city, error)
        reading = get_cached_reading(normalized_city)
        if reading is None:
            raise HTTPException(
                status_code=503,
                detail="Air-quality data is unavailable, so personalized advice cannot be generated.",
            ) from error
        reading["is_stale"] = True

    try:
        return await generate_advice(payload.profile, reading)
    except AdviceServiceError as error:
        logger.warning("Gemini advice generation failed: %s", error)
        raise HTTPException(
            status_code=502,
            detail="Personalized advice is temporarily unavailable.",
        ) from error