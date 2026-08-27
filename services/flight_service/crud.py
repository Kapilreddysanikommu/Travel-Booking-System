"""Business logic for flight_service: search, lookup, creation, and reviews."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from common.mongo import get_reviews_collection
from services.flight_service.models import Flight
from services.flight_service.schemas import FlightCreate, FlightUpdate, ReviewCreate


def list_flights(
    db: Session,
    departure_airport: Optional[str] = None,
    arrival_airport: Optional[str] = None,
    max_price: Optional[float] = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Flight]:
    """Return one page of flights matching whichever filters were actually provided."""
    query = db.query(Flight)
    if departure_airport is not None:
        query = query.filter(Flight.departure_airport == departure_airport)
    if arrival_airport is not None:
        query = query.filter(Flight.arrival_airport == arrival_airport)
    if max_price is not None:
        query = query.filter(Flight.price <= max_price)
    return query.offset(offset).limit(limit).all()


def get_flight_by_id(db: Session, flight_id: str) -> Flight | None:
    return db.query(Flight).filter(Flight.flight_id == flight_id).first()


def create_flight(db: Session, flight_data: FlightCreate) -> Flight:
    new_flight = Flight(**flight_data.model_dump())
    db.add(new_flight)
    db.commit()
    db.refresh(new_flight)
    return new_flight


def update_flight(db: Session, flight_id: str, flight_data: FlightUpdate) -> Flight | None:
    """Overwrite every mutable field on an existing flight. Returns None if it doesn't exist."""
    flight = get_flight_by_id(db, flight_id)
    if flight is None:
        return None
    for field, value in flight_data.model_dump().items():
        setattr(flight, field, value)
    db.commit()
    db.refresh(flight)
    return flight


def create_review(
    db: Session, flight_id: str, user_id: str, review_data: ReviewCreate
) -> dict | None:
    """
    Insert a review document into MongoDB, after confirming the flight
    exists in MySQL. Returns None if the flight is not found, so a review
    can never be attached to an item that does not exist.
    """
    if get_flight_by_id(db, flight_id) is None:
        return None

    review = {
        "review_id": str(uuid.uuid4()),
        "item_id": flight_id,
        "item_type": "flight",
        "user_id": user_id,
        "rating": review_data.rating,
        "comment": review_data.comment,
        "created_at": datetime.now(timezone.utc),
    }
    get_reviews_collection().insert_one(review)
    return review
