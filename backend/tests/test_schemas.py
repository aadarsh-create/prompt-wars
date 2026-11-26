import pytest
from pydantic import ValidationError

from app.schemas import AdviceRequest, UserProfile


def test_profile_accepts_supported_values():
    profile = UserProfile(
        city="delhi",
        persona="senior",
        commute="walk",
        purifier=True,
    )

    assert profile.city.value == "Delhi"
    assert profile.has_purifier is True


@pytest.mark.parametrize(
    "payload",
    [
        {"city": "London", "persona": "senior"},
        {"city": "Delhi", "persona": "unknown"},
        {"city": "Delhi", "persona": "student", "commute": "spaceship"},
    ],
)
def test_profile_rejects_invalid_values(payload):
    with pytest.raises(ValidationError):
        UserProfile.model_validate(payload)


def test_advice_request_rejects_extra_fields():
    with pytest.raises(ValidationError):
        AdviceRequest.model_validate(
            {
                "profile": {"city": "Delhi", "persona": "student"},
                "unexpected": True,
            }
        )
