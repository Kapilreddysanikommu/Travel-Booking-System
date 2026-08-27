"""
Async Kafka producer for billing_service.

FastAPI's sync `def` routes (like create_booking) run in a worker thread,
but aiokafka's AIOKafkaProducer only works with asyncio. To bridge that gap,
one producer is started on the app's main event loop at startup (see
lifespan in main.py), and sync code hands it work with
asyncio.run_coroutine_threadsafe instead of creating a new producer - and a
new event loop - per request.
"""

import asyncio
import json
import logging
import os
from decimal import Decimal

from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
BOOKING_CREATED_TOPIC = "booking.created"


async def start_producer() -> AIOKafkaProducer:
    """Create and start the one producer this service uses for its lifetime."""
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )
    await producer.start()
    return producer


async def stop_producer(producer: AIOKafkaProducer) -> None:
    await producer.stop()


def publish_booking_created(
    producer: AIOKafkaProducer,
    loop: asyncio.AbstractEventLoop,
    *,
    booking_id: str,
    user_id: str,
    booking_type: str,
    item_id: str,
    amount: Decimal,
) -> None:
    """
    Publish a booking.created event from sync request-handling code.

    Only ever called after crud.create_booking_with_billing has already
    committed - never before or in place of that commit. A publish failure
    is logged and swallowed, not raised: the booking and billing rows are
    already durable in MySQL by this point, so a Kafka outage should not
    turn an already-successful booking into a failed API response.
    """
    payload = {
        "booking_id": booking_id,
        "user_id": user_id,
        "booking_type": booking_type,
        "item_id": item_id,
        "amount": str(amount),
    }
    future = asyncio.run_coroutine_threadsafe(
        producer.send_and_wait(BOOKING_CREATED_TOPIC, value=payload),
        loop,
    )
    try:
        future.result(timeout=5)
    except Exception:
        logger.exception(
            "Failed to publish booking.created event for booking_id=%s", booking_id
        )
