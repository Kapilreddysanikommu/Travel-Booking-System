"""Pydantic schemas for ai_service."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class FlightDeal(BaseModel):
    flight_id: str
    airline: str
    departure_airport: str
    arrival_airport: str
    departure_datetime: datetime
    arrival_datetime: datetime
    flight_class: str
    price: Decimal
    group_average_price: Decimal
    pct_below_avg: Decimal
    is_deal: bool


class HotelDeal(BaseModel):
    hotel_id: str
    name: str
    city: str
    state: str
    star_rating: int
    room_type: str
    price_per_night: Decimal
    group_average_price: Decimal
    pct_below_avg: Decimal
    is_deal: bool


class DealsSnapshotResponse(BaseModel):
    last_refreshed: datetime | None
    flight_deal_count: int
    hotel_deal_count: int
    top_flight_deals: list[FlightDeal]
    top_hotel_deals: list[HotelDeal]


class RecommendRequest(BaseModel):
    """
    Request body for POST /recommend.

    origin/destination are airport codes (flight-side filters); city is a
    hotel-side filter. The seed data does not link the two - flights use
    airport codes and hotels use unrelated randomly-generated city names -
    so these are applied as independent filters, not a single "trip to the
    same place" constraint. Pass whichever ones you have.
    """

    budget: Decimal = Field(gt=0, description="Total budget for flight + hotel stay combined")
    origin: Optional[str] = None
    destination: Optional[str] = None
    city: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @model_validator(mode="after")
    def _check_date_order(self):
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class Recommendation(BaseModel):
    flight: FlightDeal
    hotel: HotelDeal
    nights: int
    total_estimated_cost: Decimal
    why_this_pick: str


class RecommendResponse(BaseModel):
    recommendations: list[Recommendation]
    message: Optional[str] = None
