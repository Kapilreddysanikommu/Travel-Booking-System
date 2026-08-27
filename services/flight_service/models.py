"""SQLAlchemy ORM model for the flights table."""

from sqlalchemy import Column, DateTime, Integer, Numeric, String

from services.flight_service.database import Base


class Flight(Base):
    __tablename__ = "flights"

    # flight_id is a client-supplied code (e.g. "AA1023"), matching how
    # real airlines identify flights - not a database-generated integer.
    flight_id = Column(String(20), primary_key=True, index=True)

    airline = Column(String(100), nullable=False)
    departure_airport = Column(String(10), nullable=False, index=True)
    arrival_airport = Column(String(10), nullable=False, index=True)
    departure_datetime = Column(DateTime, nullable=False)
    arrival_datetime = Column(DateTime, nullable=False)
    flight_class = Column(String(20), nullable=False)

    # Numeric(10, 2), not Float - money must not use binary floating point,
    # which cannot represent values like 0.10 exactly and accumulates
    # rounding errors. Numeric stores an exact decimal value instead.
    price = Column(Numeric(10, 2), nullable=False)

    seats_available = Column(Integer, nullable=False)
