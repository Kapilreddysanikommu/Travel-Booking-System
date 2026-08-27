"""Business logic for hotel_service: search, lookup, creation, and reviews."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from common.mongo import get_reviews_collection
from services.hotel_service.models import Hotel
from services.hotel_service.schemas import HotelCreate, HotelUpdate, ReviewCreate


def list_hotels(
    db: Session,
    city: Optional[str] = None,
    max_price: Optional[float] = None,
    min_star_rating: Optional[int] = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Hotel]:
    """Return one page of hotels matching whichever filters were actually provided."""
    query = db.query(Hotel)
    if city is not None:
        query = query.filter(Hotel.city == city)
    if max_price is not None:
        query = query.filter(Hotel.price_per_night <= max_price)
    if min_star_rating is not None:
        query = query.filter(Hotel.star_rating >= min_star_rating)
    return query.offset(offset).limit(limit).all()


def get_hotel_by_id(db: Session, hotel_id: str) -> Hotel | None:
    return db.query(Hotel).filter(Hotel.hotel_id == hotel_id).first()


def create_hotel(db: Session, hotel_data: HotelCreate) -> Hotel:
    new_hotel = Hotel(**hotel_data.model_dump())
    db.add(new_hotel)
    db.commit()
    db.refresh(new_hotel)
    return new_hotel


def update_hotel(db: Session, hotel_id: str, hotel_data: HotelUpdate) -> Hotel | None:
    """Overwrite every mutable field on an existing hotel. Returns None if it doesn't exist."""
    hotel = get_hotel_by_id(db, hotel_id)
    if hotel is None:
        return None
    for field, value in hotel_data.model_dump().items():
        setattr(hotel, field, value)
    db.commit()
    db.refresh(hotel)
    return hotel


def create_review(
    db: Session, hotel_id: str, user_id: str, review_data: ReviewCreate
) -> dict | None:
    """Insert a review document into MongoDB, after confirming the hotel exists."""
    if get_hotel_by_id(db, hotel_id) is None:
        return None

    review = {
        "review_id": str(uuid.uuid4()),
        "item_id": hotel_id,
        "item_type": "hotel",
        "user_id": user_id,
        "rating": review_data.rating,
        "comment": review_data.comment,
        "created_at": datetime.now(timezone.utc),
    }
    get_reviews_collection().insert_one(review)
    return review
