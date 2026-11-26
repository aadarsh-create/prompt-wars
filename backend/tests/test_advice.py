from fastapi.testclient import TestClient

from app.main import app
from app.schemas import AdviceResponse


def test_advice_endpoint_returns_structured_response(monkeypatch):
    from app.routers import advice

    reading = {
        "city": "Delhi",
        "aqi": 143,
        "category": "Moderate",
        "pm25": 91,
        "pm10": 180,
        "observed_at": "2026-11-26T10:00:00+00:00",
        "source": "OpenAQ",
        "is_stale": False,
        "station": "Test station",
    }

    async def mock_fetch_city_reading(city):
        return reading

    async def mock_generate_advice(profile, current_reading):
        assert current_reading["aqi"] == 143
        return AdviceResponse(
            daily_routine=[
                {
                    "time_slot": "Morning",
                    "action": "Use a lower-exposure route",
                    "why": "Reduce outdoor pollutant exposure.",
                }
            ],
            indoor_actions=[
                {
                    "action": "Ventilate only when outdoor air improves",
                    "why": "Limit polluted outdoor air entering indoors.",
                }
            ],
            sustainable_swaps=[
                {
                    "swap": "Use public transport",
                    "why": "Reduces emissions and limits solo-vehicle pollution.",
                }
            ],
            caution_level="Moderate",
            summary="Take sensible exposure precautions in Delhi.",
        )

    monkeypatch.setattr(advice, "fetch_city_reading", mock_fetch_city_reading)
    monkeypatch.setattr(advice, "generate_advice", mock_generate_advice)

    with TestClient(app) as client:
        response = client.post(
            "/api/advice",
            json={
                "profile": {
                    "city": "Delhi",
                    "persona": "senior",
                    "commute": "walk",
                    "purifier": True,
                }
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["caution_level"] == "Moderate"
    assert body["daily_routine"][0]["time_slot"] == "Morning"
