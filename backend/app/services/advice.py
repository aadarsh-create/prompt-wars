import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx
from pydantic import ValidationError

from app.schemas import AdviceResponse


logger = logging.getLogger(__name__)
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "advice_v3.txt"
PROMPT_VERSION = "v3"


class AdviceServiceError(Exception):
    pass


def _load_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except OSError as error:
        raise AdviceServiceError("Advice prompt configuration is unavailable.") from error


def build_prompt(profile: Any, reading: dict[str, Any]) -> str:
    template = _load_prompt()
    context = {
        "city": profile.city.value,
        "persona": profile.persona.value,
        "commute_mode": profile.commute_mode.value,
        "has_purifier": "yes" if profile.has_purifier else "no",
        "aqi": reading["aqi"],
        "category": reading["category"],
        "pm25": reading["pm25"],
        "pm10": reading["pm10"],
        "observed_at": reading["observed_at"],
        "is_stale": "yes" if reading["is_stale"] else "no",
        "source": reading["source"],
        "station": reading.get("station") or "not reported",
    }
    prompt = template
    for key, value in context.items():
        prompt = prompt.replace("{" + key + "}", str(value))
    return prompt


def _extract_text(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise AdviceServiceError("Gemini returned no response candidates.")
    content = candidates[0].get("content") if isinstance(candidates[0], dict) else None
    parts = content.get("parts") if isinstance(content, dict) else None
    if not isinstance(parts, list):
        raise AdviceServiceError("Gemini returned an invalid response.")
    text = "".join(
        part.get("text", "")
        for part in parts
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    )
    if not text:
        raise AdviceServiceError("Gemini returned empty advice.")
    return text


def _parse_advice(text: str) -> AdviceResponse:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    try:
        payload = json.loads(cleaned)
        return AdviceResponse.model_validate(payload)
    except (json.JSONDecodeError, ValidationError) as error:
        raise AdviceServiceError("Gemini returned advice in an invalid format.") from error


async def call_gemini(prompt: str) -> AdviceResponse:
    api_key = os.getenv("GEMINI_KEY")
    if not api_key:
        raise AdviceServiceError("GEMINI_KEY is not configured.")

    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    response_schema = {
        "type": "object",
        "properties": {
            "daily_routine": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "time_slot": {"type": "string"},
                        "action": {"type": "string"},
                        "why": {"type": "string"},
                    },
                    "required": ["time_slot", "action", "why"],
                },
            },
            "indoor_actions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string"},
                        "why": {"type": "string"},
                    },
                    "required": ["action", "why"],
                },
            },
            "sustainable_swaps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "swap": {"type": "string"},
                        "why": {"type": "string"},
                    },
                    "required": ["swap", "why"],
                },
            },
            "caution_level": {"type": "string"},
            "summary": {"type": "string"},
        },
        "required": [
            "daily_routine",
            "indoor_actions",
            "sustainable_swaps",
            "caution_level",
            "summary",
        ],
    }
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "responseMimeType": "application/json",
            "responseSchema": response_schema,
        },
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        for attempt in range(2):
            try:
                response = await client.post(url, params={"key": api_key}, json=body)
            except httpx.HTTPError as error:
                if attempt == 0:
                    continue
                raise AdviceServiceError("Unable to reach the Gemini API.") from error
            if response.status_code >= 500 and attempt == 0:
                continue
            if response.is_error:
                raise AdviceServiceError("Gemini advice generation failed.")
            try:
                payload = response.json()
            except ValueError as error:
                raise AdviceServiceError("Gemini returned invalid JSON.") from error
            try:
                return _parse_advice(_extract_text(payload))
            except AdviceServiceError as error:
                if attempt == 0:
                    continue
                raise error

    raise AdviceServiceError("Gemini advice generation failed.")


async def generate_advice(profile: Any, reading: dict[str, Any]) -> AdviceResponse:
    prompt = build_prompt(profile, reading)
    return await call_gemini(prompt)