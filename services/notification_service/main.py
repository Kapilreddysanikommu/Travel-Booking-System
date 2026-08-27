"""
notification_service: consumes booking.created events and logs a
confirmation message. Stands in for what would eventually be a real
notification (email/SMS/push) - the logging is the whole feature for now.
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager

from aiokafka import AIOKafkaConsumer
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
BOOKING_CREATED_TOPIC = "booking.created"


async def consume_booking_created() -> None:
    """
    Long-running loop: read booking.created events one at a time and log them.

    group_id makes this consumer part of a named consumer group - Kafka
    remembers this group's last-read offset per partition, so a restart
    resumes after the last message actually processed instead of replaying
    the whole topic or silently skipping messages that arrived meanwhile.

    auto_offset_reset="earliest" only matters the first time this group_id
    is ever seen (no committed offset yet): it means start from the
    beginning of the topic rather than only messages published from now on -
    convenient for a demo where the consumer may start after the producer.
    """
    consumer = AIOKafkaConsumer(
        BOOKING_CREATED_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="notification_service",
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        auto_offset_reset="earliest",
    )
    await consumer.start()
    try:
        async for message in consumer:
            event = message.value
            logger.info(
                "Booking confirmed for user %s (booking_id=%s, %s %s, amount=%s)",
                event["user_id"],
                event["booking_id"],
                event["booking_type"],
                event["item_id"],
                event["amount"],
            )
    finally:
        await consumer.stop()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs the consumer loop as a background task alongside the web server,
    # rather than as the app's main body, so /health can still respond while
    # consume_booking_created() blocks on new messages forever.
    consumer_task = asyncio.create_task(consume_booking_created())
    yield
    consumer_task.cancel()


app = FastAPI(title="Notification Service", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "service": "notification_service"}
