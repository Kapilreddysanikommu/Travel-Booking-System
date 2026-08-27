"""
Shared Redis connection for cache-aside lookups (flight/hotel by id).

redis-py manages its own connection pool internally, so - same reasoning
as common/mongo.py's single shared MongoClient - one client is created
once at import time and reused, rather than opened and closed per request.
"""

import os

from dotenv import load_dotenv
from redis import Redis

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# decode_responses=True means values come back as str, not bytes - every
# caller here stores/reads JSON text, so this avoids a manual .decode() at
# every call site.
_client = Redis.from_url(REDIS_URL, decode_responses=True)


def get_redis() -> Redis:
    """Return the shared Redis client used by all services."""
    return _client
