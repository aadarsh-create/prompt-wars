from fastapi import APIRouter

from app.schemas import SUPPORTED_CITIES


router = APIRouter(tags=["cities"])


@router.get("/cities")
def get_cities() -> dict[str, list[str]]:
    return {"cities": list(SUPPORTED_CITIES)}
