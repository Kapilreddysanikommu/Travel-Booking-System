"""Background asyncio task that refreshes the deals snapshot on a fixed interval."""

import asyncio
import logging

from services.ai_service.database import SessionLocal
from services.ai_service.deals_agent import compute_flight_deals, compute_hotel_deals
from services.ai_service.deals_store import set_snapshot

logger = logging.getLogger(__name__)

REFRESH_INTERVAL_SECONDS = 60


def refresh_deals_once() -> None:
    """Run one refresh cycle: read flights/hotels, score them, publish the snapshot."""
    db = SessionLocal()
    try:
        flight_deals = compute_flight_deals(db)
        hotel_deals = compute_hotel_deals(db)
        set_snapshot(flight_deals, hotel_deals)
        logger.info(
            "Deals refreshed: %d flights (%d deals), %d hotels (%d deals)",
            len(flight_deals),
            sum(1 for d in flight_deals if d["is_deal"]),
            len(hotel_deals),
            sum(1 for d in hotel_deals if d["is_deal"]),
        )
    finally:
        db.close()


async def run_deals_refresh_loop() -> None:
    """
    Refresh immediately on startup, then every REFRESH_INTERVAL_SECONDS.

    Runs the blocking DB/CPU work in a thread via asyncio.to_thread so it
    never stalls the event loop that's also serving /recommend requests.
    A single unhandled exception here would otherwise kill the task
    silently, so a failed cycle is logged and the loop keeps running rather
    than exiting the whole background task.
    """
    while True:
        try:
            await asyncio.to_thread(refresh_deals_once)
        except Exception:
            logger.exception("Deals refresh cycle failed")
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)
