"""billing_service: create bookings+billing atomically, and look them up."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from common.auth import get_current_user
from services.billing_service import crud
from services.billing_service.database import Base, engine, get_db
from services.billing_service.kafka_producer import (
    publish_booking_created,
    start_producer,
    stop_producer,
)
from services.billing_service.schemas import BillingResponse, BookingCreate, BookingCreateResponse

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # One producer, started on this event loop, lives for the app's whole
    # lifetime - not one per request. app.state is FastAPI's sanctioned
    # place to stash things a request handler needs but that aren't
    # per-request data (a DB session, a Depends value, etc).
    app.state.kafka_producer = await start_producer()
    app.state.kafka_loop = asyncio.get_event_loop()
    yield
    await stop_producer(app.state.kafka_producer)


app = FastAPI(title="Billing Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "billing_service"}


@app.post("/bookings", response_model=BookingCreateResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    booking_data: BookingCreate,
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    try:
        booking, billing = crud.create_booking_with_billing(db, booking_data)
    except SQLAlchemyError:
        # log the real exception (with traceback) here - the HTTPException
        # below intentionally hides DB internals from the API response, so
        # this is the only place the actual cause ever gets recorded.
        logger.exception("create_booking_with_billing failed for user_id=%s", booking_data.user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Booking could not be completed - no booking or billing record was created",
        )

    # Only reached once the transaction above has actually committed - the
    # booking and billing rows are already durable in MySQL, so publishing
    # here can never announce a booking that turns out not to exist.
    publish_booking_created(
        request.app.state.kafka_producer,
        request.app.state.kafka_loop,
        booking_id=booking.booking_id,
        user_id=booking.user_id,
        booking_type=booking.booking_type,
        item_id=booking.item_id,
        amount=billing.amount,
    )

    return BookingCreateResponse(booking=booking, billing=billing)


@app.get("/bookings/user/{user_id}", response_model=list[BillingResponse])
def list_user_bookings(
    user_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    return crud.list_billing_by_user(db, user_id)


@app.get("/bookings/{billing_id}", response_model=BillingResponse)
def get_booking(billing_id: str, db: Session = Depends(get_db)):
    billing = crud.get_billing_by_id(db, billing_id)
    if billing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return billing
