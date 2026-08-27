"""Pydantic schemas for billing_service."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class BookingCreate(BaseModel):
    """
    Request body for POST /bookings.

    booking_type uses Literal["flight", "hotel"] instead of a plain str
    plus a manual check - Pydantic rejects any other value automatically
    (422 response) before this data ever reaches business logic.
    """

    user_id: str
    booking_type: Literal["flight", "hotel"]
    item_id: str
    amount: Decimal
    payment_method: str


class BookingResponse(BaseModel):
    booking_id: str
    user_id: str
    booking_type: str
    item_id: str
    booking_date: datetime
    status: str

    class Config:
        from_attributes = True


class BillingResponse(BaseModel):
    billing_id: str
    user_id: str
    booking_type: str
    booking_id: str
    transaction_date: datetime
    amount: Decimal
    payment_method: str
    status: str

    class Config:
        from_attributes = True


class BookingCreateResponse(BaseModel):
    """Combined response for POST /bookings - both records created together."""

    booking: BookingResponse
    billing: BillingResponse
