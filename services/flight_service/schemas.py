"""Pydantic schemas for flight_service."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class FlightCreate(BaseModel):
    """Request body for POST /flights."""

    flight_id: str
    airline: str
    departure_airport: str
    arrival_airport: str
    departure_datetime: datetime
    arrival_datetime: datetime
    flight_class: str
    price: Decimal
    seats_available: int


class FlightResponse(BaseModel):
    flight_id: str
    airline: str
    departure_airport: str
    arrival_airport: str
    departure_datetime: datetime
    arrival_datetime: datetime
    flight_class: str
    price: Decimal
    seats_available: int

    class Config:
        from_attributes = True


class FlightUpdate(BaseModel):
    """Request body for PUT /flights/{flight_id} - flight_id comes from the path, not the body."""

    airline: str
    departure_airport: str
    arrival_airport: str
    departure_datetime: datetime
    arrival_datetime: datetime
    flight_class: str
    price: Decimal
    seats_available: int


class ReviewCreate(BaseModel):
    """
    Request body for POST /reviews/flights/{flight_id}.

    Only rating and comment come from the client - item_id comes from the
    URL path and user_id comes from the JWT, never from the request body.
    Trusting a client-supplied user_id would let anyone post a review
    under someone else's identity.
    """

    rating: int = Field(ge=1, le=5)
    comment: str


class ReviewResponse(BaseModel):
    review_id: str
    item_id: str
    item_type: str
    user_id: str
    rating: int
    comment: str
    created_at: datetime
