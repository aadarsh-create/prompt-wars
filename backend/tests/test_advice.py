import asyncio

import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import AdviceResponse
from app.services import aqi_cache
from app.services import advice as advice_service
from app.services.aqi_client import OpenAQError


def clear_advice_cache():
    with aqi_cache._lock:
        aqi_cache._cache.clear()


def test_advice_endpoint_accepts_a_mocked_gemini_response(monkeypatch):
    real_async_client = httpx.AsyncClient
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": (
                                        '{"daily_routine":[{"time_slot":"Morning",'
                                        '"action":"Take a lower-exposure route",'
                                        '"why":"It limits time near traffic."}],'
                                        '"indoor_actions":[{"action":"Ventilate briefly",'
                                        '"why":"Use cleaner outdoor periods."}],'
                                        '"sustainable_swaps":[{"swap":"Use public transport",'
                                        '"why":"It reduces emissions and exposure."}],'
                                        '"caution_level":"Moderate",'
                                        '"summary":"Use sensible precautions in Delhi."}'
                                    )
                                }
                            ]
                        }
                    }
                ]
            },
        )
    )

    def mock_async_client(**kwargs):
        return real_async_client(transport=transport, timeout=kwargs["timeout"])

    monkeypatch.setenv("GEMINI_KEY", "test-key")
    monkeypatch.setattr(advice_service.httpx, "AsyncClient", mock_async_client)

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

    monkeypatch.setattr(advice, "fetch_city_reading", mock_fetch_city_reading)

    clear_advice_cache()
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


def test_advice_endpoint_marks_cached_reading_stale(monkeypatch):
    from app.routers import advice

    cached = {
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
    aqi_cache.cache_reading("Delhi", cached)

    async def provider_failure(city):
        raise OpenAQError("provider unavailable")

    async def mock_generate_advice(profile, current_reading):
        assert current_reading["is_stale"] is True
        return AdviceResponse(
            daily_routine=[
                {"time_slot": "Morning", "action": "Limit exposure", "why": "Use caution."}
            ],
            indoor_actions=[
                {"action": "Close windows", "why": "Reduce outdoor pollution indoors."}
            ],
            sustainable_swaps=[
                {"swap": "Use public transport", "why": "Lower emissions."}
            ],
            caution_level="Moderate",
            summary="This is a stale reading used only as a cautionary signal.",
        )

    monkeypatch.setattr(advice, "fetch_city_reading", provider_failure)
    monkeypatch.setattr(advice, "generate_advice", mock_generate_advice)

    with TestClient(app) as client:
        response = client.post(
            "/api/advice",
            json={"profile": {"city": "Delhi", "persona": "senior"}},
        )

    assert response.status_code == 200
    clear_advice_cache()


def test_advice_endpoint_returns_503_without_reading_or_cache(monkeypatch):
    from app.routers import advice

    clear_advice_cache()

    async def provider_failure(city):
        raise OpenAQError("provider unavailable")

    monkeypatch.setattr(advice, "fetch_city_reading", provider_failure)

    with TestClient(app) as client:
        response = client.post(
            "/api/advice",
            json={"profile": {"city": "Mumbai", "persona": "student"}},
        )

    assert response.status_code == 503
    assert "cannot be generated" in response.json()["detail"]


def test_advice_endpoint_returns_502_when_gemini_fails(monkeypatch):
    from app.routers import advice

    async def mock_fetch_city_reading(city):
        return {
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

    async def mock_generate_advice(profile, reading):
        raise advice_service.AdviceServiceError("Gemini unavailable")

    monkeypatch.setattr(advice, "fetch_city_reading", mock_fetch_city_reading)
    monkeypatch.setattr(advice, "generate_advice", mock_generate_advice)

    with TestClient(app) as client:
        response = client.post(
            "/api/advice",
            json={"profile": {"city": "Delhi", "persona": "working_professional"}},
        )

    assert response.status_code == 502
    assert "temporarily unavailable" in response.json()["detail"]


def test_advice_service_rejects_malformed_gemini_json(monkeypatch):
    real_async_client = httpx.AsyncClient
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "not json"}]}}]},
        )
    )

    def mock_async_client(**kwargs):
        return real_async_client(transport=transport, timeout=kwargs["timeout"])

    monkeypatch.setenv("GEMINI_KEY", "test-key")
    monkeypatch.setattr(advice_service.httpx, "AsyncClient", mock_async_client)

    try:
        asyncio.run(advice_service.call_gemini("test prompt"))
    except advice_service.AdviceServiceError as error:
        assert "invalid format" in str(error)
    else:
        raise AssertionError("Malformed Gemini JSON should raise AdviceServiceError")


def test_advice_service_loads_prompt_v3(monkeypatch):
    assert advice_service.PROMPT_VERSION == "v3"
    assert advice_service.PROMPT_PATH.name == "advice_v3.txt"

    profile = type(
        "Profile",
        (),
        {
            "city": type("City", (), {"value": "Delhi"})(),
            "persona": type("Persona", (), {"value": "child_family"})(),
            "commute_mode": type("Commute", (), {"value": "none"})(),
            "has_purifier": True,
        },
    )()
    reading = {
        "aqi": 301,
        "category": "Very Poor",
        "pm25": 220,
        "pm10": 330,
        "observed_at": "2026-11-26T10:00:00+00:00",
        "is_stale": False,
        "source": "OpenAQ",
        "station": "Test station",
    }

    prompt = advice_service.build_prompt(profile, reading)

    assert "City: Delhi" in prompt
    assert "child_family" in prompt
    assert "Is stale: no" in prompt
    assert "explicit \"go\", \"limited\", or \"no-go\" decision" in prompt
    assert "For severe winter smog" in prompt
    assert "brief ventilation only when outdoor air is known to be cleaner" in prompt
    assert "Do not present houseplants as an effective substitute" in prompt


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
