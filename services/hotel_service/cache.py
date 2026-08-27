"""
Redis cache-aside helpers for hotel lookups by id. Same pattern as
services/flight_service/cache.py - see that file for the full rationale.
"""

import json

from common.redis_client import get_redis
from services.hotel_service.schemas import HotelResponse

CACHE_TTL_SECONDS = 300


def _cache_key(hotel_id: str) -> str:
    return f"hotel:{hotel_id}"


def get_cached_hotel(hotel_id: str) -> dict | None:
    cached = get_redis().get(_cache_key(hotel_id))
    if cached is None:
        return None
    return json.loads(cached)


def cache_hotel(hotel_id: str, hotel: HotelResponse) -> None:
    payload = hotel.model_dump(mode="json")
    get_redis().setex(_cache_key(hotel_id), CACHE_TTL_SECONDS, json.dumps(payload))


def invalidate_hotel_cache(hotel_id: str) -> None:
    get_redis().delete(_cache_key(hotel_id))
