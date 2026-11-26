from enum import Enum
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
    pm25_observed_at: str | None = None
    pm10_observed_at: str | None = None


ProfileRequest = UserProfile
