from threading import Lock
from typing import Any


_cache: dict[str, dict[str, Any]] = {}
_lock = Lock()


def get_cached_reading(city: str) -> dict[str, Any] | None:
    with _lock:
        reading = _cache.get(city.casefold())
        return reading.copy() if reading is not None else None


def cache_reading(city: str, reading: dict[str, Any]) -> None:
    with _lock:
        _cache[city.casefold()] = reading.copy()