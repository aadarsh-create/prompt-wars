from enum import Enum
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


SUPPORTED_CITIES = (
    "Delhi",
    "Mumbai",
    "Kolkata",
    "Chennai",
    "Bengaluru",
    "Hyderabad",
)

class City(str, Enum):
    DELHI = "Delhi"
    MUMBAI = "Mumbai"
    KOLKATA = "Kolkata"
    CHENNAI = "Chennai"
    BENGALURU = "Bengaluru"
    HYDERABAD = "Hyderabad"


class Persona(str, Enum):
    CHILD_FAMILY = "child_family"
    SENIOR = "senior"
    WORKING_PROFESSIONAL = "working_professional"
    STUDENT = "student"


class CommuteMode(str, Enum):
    WALK = "walk"
    CYCLE = "cycle"
    PUBLIC_TRANSPORT = "public_transport"
    CAR = "car"
    NONE = "none"


CityName = City
PersonaName = Persona


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AQIQuery(StrictModel):
    city: CityName


class UserProfile(StrictModel):
    city: CityName
    persona: PersonaName
    commute_mode: CommuteMode = Field(
        default="none",
        validation_alias=AliasChoices("commute_mode", "commute"),
        serialization_alias="commute_mode",
    )
    has_purifier: bool = Field(
        default=False,
        validation_alias=AliasChoices("has_purifier", "purifier"),
        serialization_alias="has_purifier",
    )

    @field_validator("city", mode="before")
    @classmethod
    def normalize_city(cls, value):
        if isinstance(value, str):
            normalized = value.strip().casefold()
            for city in City:
                if city.value.casefold() == normalized:
                    return city
        return value


class AdviceRequest(StrictModel):
    profile: UserProfile


class AQIHistoryPoint(StrictModel):
    timestamp: str
    aqi: int = Field(ge=0, le=500)


class AQIReading(StrictModel):
    city: str
    aqi: int = Field(ge=0, le=500)
    category: str
    pm25: float = Field(ge=0)
    pm10: float = Field(ge=0)
    observed_at: str
    source: str
    is_stale: bool
    station: str | None = None
    temperature_c: float | None = Field(default=None, ge=-90, le=70)
    pm25_observed_at: str | None = None
    pm10_observed_at: str | None = None
    history: list[AQIHistoryPoint] = Field(default_factory=list)
    history_parameter: Literal["pm25", "pm10", "both"] | None = None


class DailyRoutineItem(StrictModel):
    time_slot: str = Field(min_length=1)
    action: str = Field(min_length=1)
    why: str = Field(min_length=1)


class IndoorAction(StrictModel):
    action: str = Field(min_length=1)
    why: str = Field(min_length=1)


class SustainableSwap(StrictModel):
    swap: str = Field(min_length=1)
    why: str = Field(min_length=1)


class AdviceResponse(StrictModel):
    daily_routine: list[DailyRoutineItem] = Field(min_length=1)
    indoor_actions: list[IndoorAction] = Field(min_length=1)
    sustainable_swaps: list[SustainableSwap] = Field(min_length=1)
    caution_level: str = Field(min_length=1)
    summary: str = Field(min_length=1)

    @field_validator("indoor_actions", mode="before")
    @classmethod
    def normalize_indoor_actions(cls, value):
        if not isinstance(value, list):
            return value
        return [
            {"action": item, "why": "Reduce indoor exposure to polluted outdoor air."}
            if isinstance(item, str)
            else item
            for item in value
        ]


ProfileRequest = UserProfile
