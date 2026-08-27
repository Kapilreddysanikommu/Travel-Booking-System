"""
Populates local databases with realistic sample data for testing:
1,000 users, 10,000 flights, 10,000 hotels, and 5,000 booking+billing pairs.

Uses SQLAlchemy Core bulk inserts (not one ORM object per row) because this
is a one-shot bulk load - the ORM's per-object change tracking is overhead
we don't need here, and Core inserts at this volume run in seconds instead
of minutes.

Run from the repo root: python seed_data.py
Requires: pip install -r services/user_service/requirements.txt faker
"""

import os
import random
import uuid
from datetime import timedelta
from decimal import Decimal

from dotenv import load_dotenv
from faker import Faker
from passlib.context import CryptContext
from sqlalchemy import create_engine, insert

from services.billing_service.models import Billing, Booking
from services.billing_service.models import Base as BillingBase
from services.flight_service.models import Flight
from services.flight_service.models import Base as FlightBase
from services.hotel_service.models import Hotel
from services.hotel_service.models import Base as HotelBase
from services.user_service.models import User
from services.user_service.models import Base as UserBase

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "mysql+pymysql://travel_app:app_password@localhost:3307/travel_booking"
)

# .env's DATABASE_URL uses host "mysql" - that name only resolves inside
# Docker's internal network (docker-compose registers it there for the
# service containers). This script runs as a plain process on your machine,
# outside that network, so it needs the port docker-compose publishes to the
# host instead: localhost:3307 (see the "3307:3306" mapping in
# docker-compose.yml). The database itself doesn't change - only how a
# process outside the containers reaches it.
if "@mysql:" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("@mysql:3306", "@localhost:3307")

engine = create_engine(DATABASE_URL)
fake = Faker("en_US")

NUM_USERS = 1000
NUM_FLIGHTS = 10000
NUM_HOTELS = 10000
NUM_BOOKINGS = 5000
BATCH_SIZE = 1000

# All seeded users share this password - real password hashing (bcrypt) is
# deliberately slow to resist brute-force attacks, so hashing it once and
# reusing the hash avoids a multi-minute seed run. Never do this for real
# user data, only throwaway local test data.
SEED_PASSWORD_HASH = CryptContext(schemes=["bcrypt"]).hash("Password123!")

AIRLINES = [
    ("American Airlines", "AA"), ("Delta Air Lines", "DL"), ("United Airlines", "UA"),
    ("Southwest Airlines", "WN"), ("JetBlue Airways", "B6"), ("Alaska Airlines", "AS"),
    ("Spirit Airlines", "NK"), ("Frontier Airlines", "F9"), ("Hawaiian Airlines", "HA"),
    ("Allegiant Air", "G4"),
]
AIRPORT_CODES = [
    "JFK", "LAX", "ORD", "ATL", "DFW", "DEN", "SFO", "SEA", "LAS", "MCO",
    "MIA", "PHX", "IAH", "BOS", "EWR", "MSP", "DTW", "PHL", "LGA", "CLT",
    "FLL", "BWI", "SLC", "SAN", "IAD", "TPA", "PDX", "STL", "HNL", "AUS",
]
FLIGHT_CLASSES = ["Economy", "Premium Economy", "Business", "First"]
ROOM_TYPES = ["Standard", "Deluxe", "Suite", "Executive"]
AMENITIES_POOL = [
    "wifi", "pool", "gym", "parking", "breakfast", "spa",
    "pet_friendly", "air_conditioning", "room_service", "bar",
]
PAYMENT_METHODS = ["credit_card", "debit_card", "paypal", "gift_card"]


def create_tables():
    """Create every service's tables against this one MySQL database."""
    UserBase.metadata.create_all(bind=engine)
    FlightBase.metadata.create_all(bind=engine)
    HotelBase.metadata.create_all(bind=engine)
    BillingBase.metadata.create_all(bind=engine)


def insert_batches(table, rows):
    """Bulk-insert rows in fixed-size batches to keep memory use bounded."""
    with engine.begin() as conn:
        for i in range(0, len(rows), BATCH_SIZE):
            conn.execute(insert(table), rows[i : i + BATCH_SIZE])


def seed_users() -> list[str]:
    rows = []
    seen_ids = set()
    while len(rows) < NUM_USERS:
        user_id = fake.ssn()
        if user_id in seen_ids:
            continue
        seen_ids.add(user_id)
        rows.append({
            "user_id": user_id,
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "address": fake.street_address(),
            "city": fake.city(),
            "state": fake.state_abbr(include_territories=False),
            "zip_code": fake.zipcode(),
            "phone": fake.phone_number()[:20],
            "email": fake.unique.email(),
            "hashed_password": SEED_PASSWORD_HASH,
        })
    insert_batches(User.__table__, rows)
    return [r["user_id"] for r in rows]


def seed_flights() -> list[str]:
    rows = []
    for i in range(NUM_FLIGHTS):
        airline_name, airline_code = random.choice(AIRLINES)
        departure_airport, arrival_airport = random.sample(AIRPORT_CODES, 2)
        departure = fake.date_time_between(start_date="+1d", end_date="+180d")
        arrival = departure + timedelta(
            hours=random.randint(1, 14), minutes=random.randint(0, 59)
        )
        rows.append({
            # The 1000+i suffix is unique per row regardless of the random
            # airline code prefix, so no duplicate-checking is needed.
            "flight_id": f"{airline_code}{1000 + i}",
            "airline": airline_name,
            "departure_airport": departure_airport,
            "arrival_airport": arrival_airport,
            "departure_datetime": departure,
            "arrival_datetime": arrival,
            "flight_class": random.choice(FLIGHT_CLASSES),
            "price": Decimal(random.randrange(5000, 200000)) / 100,
            "seats_available": random.randint(0, 300),
        })
    insert_batches(Flight.__table__, rows)
    return [r["flight_id"] for r in rows]


def seed_hotels() -> list[str]:
    rows = []
    for i in range(NUM_HOTELS):
        rows.append({
            "hotel_id": f"HT{100000 + i}",
            "name": f"{fake.company()} Hotel",
            "address": fake.street_address(),
            "city": fake.city(),
            "state": fake.state_abbr(include_territories=False),
            "zip_code": fake.zipcode(),
            "star_rating": random.randint(1, 5),
            "room_type": random.choice(ROOM_TYPES),
            "price_per_night": Decimal(random.randrange(5000, 60000)) / 100,
            "amenities": random.sample(AMENITIES_POOL, k=random.randint(2, 6)),
        })
    insert_batches(Hotel.__table__, rows)
    return [r["hotel_id"] for r in rows]


def seed_bookings_and_billing(user_ids, flight_ids, hotel_ids):
    booking_rows = []
    billing_rows = []
    for _ in range(NUM_BOOKINGS):
        booking_id = str(uuid.uuid4())
        user_id = random.choice(user_ids)
        booking_type = random.choice(["flight", "hotel"])
        item_id = random.choice(flight_ids) if booking_type == "flight" else random.choice(hotel_ids)
        booking_date = fake.date_time_between(start_date="-180d", end_date="now")

        booking_rows.append({
            "booking_id": booking_id,
            "user_id": user_id,
            "booking_type": booking_type,
            "item_id": item_id,
            "booking_date": booking_date,
            "status": random.choice(["confirmed", "cancelled"]),
        })
        billing_rows.append({
            "billing_id": str(uuid.uuid4()),
            "user_id": user_id,
            "booking_type": booking_type,
            "booking_id": booking_id,
            "transaction_date": booking_date,
            "amount": Decimal(random.randrange(5000, 200000)) / 100,
            "payment_method": random.choice(PAYMENT_METHODS),
            "status": random.choice(["completed", "failed", "pending"]),
        })

    # Bookings must be inserted before billing - billing.booking_id is a
    # real foreign key into bookings.booking_id, same as in the live API.
    insert_batches(Booking.__table__, booking_rows)
    insert_batches(Billing.__table__, billing_rows)


def main():
    print("Creating tables if they do not already exist...")
    create_tables()

    print(f"Seeding {NUM_USERS} users...")
    user_ids = seed_users()

    print(f"Seeding {NUM_FLIGHTS} flights...")
    flight_ids = seed_flights()

    print(f"Seeding {NUM_HOTELS} hotels...")
    hotel_ids = seed_hotels()

    print(f"Seeding {NUM_BOOKINGS} bookings and billing records...")
    seed_bookings_and_billing(user_ids, flight_ids, hotel_ids)

    print("Done. All seeded users share the password: Password123!")


if __name__ == "__main__":
    main()
