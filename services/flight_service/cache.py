"""
Redis cache-aside helpers for flight lookups by id.

Only GET /flights/{flight_id} is cached - not the paginated /flights search.
A single flight_id lookup is one key holding one small object, which is what
cache-aside fits naturally; search results depend on an open-ended
combination of filters, offset, and limit, which would need a much more
elaborate (and easy to get wrong) cache key scheme to pay off.
"""

import json

from common.redis_client import get_redis
from services.flight_service.schemas import FlightResponse

# Bounds how long a missed invalidation can serve stale data - see
# common/redis_client.py for the shared client this reads/writes through.
CACHE_TTL_SECONDS = 300


def _cache_key(flight_id: str) -> str:
    return f"flight:{flight_id}"


def get_cached_flight(flight_id: str) -> dict | None:
    cached = get_redis().get(_cache_key(flight_id))
    if cached is None:
        return None
    return json.loads(cached)


def cache_flight(flight_id: str, flight: FlightResponse) -> None:
    payload = flight.model_dump(mode="json")
    get_redis().setex(_cache_key(flight_id), CACHE_TTL_SECONDS, json.dumps(payload))


def invalidate_flight_cache(flight_id: str) -> None:
    get_redis().delete(_cache_key(flight_id))
