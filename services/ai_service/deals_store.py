"""
In-memory store for the current deal scores.

Chosen over Redis for this piece deliberately: the scores are recomputed
from scratch every refresh cycle (nothing here needs to survive a restart),
they're only ever read by this same process, and a plain module-level
variable means every request sees a fully-computed snapshot with no
serialize/deserialize cost. A dict/list reassignment in Python is atomic
under the GIL, so a reader can never observe a half-written refresh.

The tradeoff: this only works because ai_service runs as a single process.
If it were ever scaled to multiple workers/replicas behind a load balancer,
each would compute and hold its own copy, which is wasteful (N processes
all hitting MySQL every 60s) and means two requests could hit two workers
with different snapshots. That's exactly the case Redis - a cache every
worker reads from - is built for, and is what flight_service/hotel_service
already use for their own lookups (see common/redis_client.py). It just
isn't needed yet for a single-process learning service.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class DealsSnapshot:
    flight_deals: list[dict] = field(default_factory=list)
    hotel_deals: list[dict] = field(default_factory=list)
    last_refreshed: datetime | None = None


_snapshot = DealsSnapshot()


def get_snapshot() -> DealsSnapshot:
    return _snapshot


def set_snapshot(flight_deals: list[dict], hotel_deals: list[dict]) -> None:
    global _snapshot
    _snapshot = DealsSnapshot(
        flight_deals=flight_deals,
        hotel_deals=hotel_deals,
        last_refreshed=datetime.now(timezone.utc),
    )
