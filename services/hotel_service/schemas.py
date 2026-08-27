"""Pydantic schemas for hotel_service."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class HotelCreate(BaseModel):
    """Request body for POST /hotels."""

    hotel_id: str
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    star_rating: int = Field(ge=1, le=5)
    room_type: str
    price_per_night: Decimal
    amenities: list[str]


class HotelResponse(BaseModel):
    hotel_id: str
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    star_rating: int
    room_type: str
    price_per_night: Decimal
    amenities: list[str]

    class Config:
        from_attributes = True


class HotelUpdate(BaseModel):
    """Request body for PUT /hotels/{hotel_id} - hotel_id comes from the path, not the body."""

    name: str
    address: str
    city: str
    state: str
    zip_code: str
    star_rating: int = Field(ge=1, le=5)
    room_type: str
    price_per_night: Decimal
    amenities: list[str]


class ReviewCreate(BaseModel):
    """Only rating/comment come from the client - see flight_service for why."""

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
