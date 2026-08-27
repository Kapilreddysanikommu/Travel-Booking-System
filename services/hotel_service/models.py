"""SQLAlchemy ORM model for the hotels table."""

from sqlalchemy import JSON, Column, Integer, Numeric, String

from services.hotel_service.database import Base


class Hotel(Base):
    __tablename__ = "hotels"

    hotel_id = Column(String(20), primary_key=True, index=True)

    name = Column(String(150), nullable=False)
    address = Column(String(200), nullable=False)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(2), nullable=False)
    zip_code = Column(String(10), nullable=False)
    star_rating = Column(Integer, nullable=False)
    room_type = Column(String(50), nullable=False)
    price_per_night = Column(Numeric(10, 2), nullable=False)

    # Stored as a JSON list (e.g. ["pool", "wifi", "gym"]) rather than a
    # comma-separated string, so it round-trips as a real Python list
    # instead of needing manual split/join parsing at every call site.
    amenities = Column(JSON, nullable=False)
