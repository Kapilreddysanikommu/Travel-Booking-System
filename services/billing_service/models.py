"""SQLAlchemy ORM models for the bookings and billing tables."""

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String

from services.billing_service.database import Base


class Booking(Base):
    __tablename__ = "bookings"

    booking_id = Column(String(36), primary_key=True, index=True)

    # user_id references a row owned by user_service's database. No real
    # foreign key is possible across separate services/databases, so
    # existence is not enforced here - only within-database references
    # (like billing.booking_id below) get a real FK constraint.
    user_id = Column(String(11), nullable=False, index=True)
    booking_type = Column(String(10), nullable=False)

    # item_id is a flight_id or hotel_id, depending on booking_type - same
    # cross-service limitation as user_id above applies.
    item_id = Column(String(20), nullable=False)

    booking_date = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default="confirmed")


class Billing(Base):
    __tablename__ = "billing"

    billing_id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(11), nullable=False, index=True)
    booking_type = Column(String(10), nullable=False)

    # This FK is real and MySQL-enforced, because bookings and billing
    # live in the same database owned by this same service - MySQL will
    # reject a billing insert that points at a booking_id that does not
    # exist in the bookings table.
    booking_id = Column(String(36), ForeignKey("bookings.booking_id"), nullable=False, index=True)

    transaction_date = Column(DateTime, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)
