# Travel Booking System

A Python/FastAPI backend split into 4 independent microservices, sharing one
MySQL instance (separate tables per service) and one MongoDB instance (for
reviews).

- User Service — port 8001
- Flight Service — port 8002
- Hotel Service — port 8003
- Billing Service — port 8004

## How to run

1. Copy `.env.example` to `.env` and fill in real values (or keep the
   defaults for local dev):

   ```
   cp .env.example .env
   ```

2. Start everything:

   ```
   docker-compose up --build
   ```

   This starts MySQL, MongoDB, and all 4 services. Each service waits for
   its databases to pass a healthcheck before starting.

3. (Optional) Populate sample data - 1,000 users, 10,000 flights, 10,000
   hotels, 5,000 bookings:

   ```
   pip install -r services/user_service/requirements.txt faker
   python seed_data.py
   ```

   All seeded users share the password `Password123!` (see `seed_data.py`
   for why - real user passwords should never be reused like this).

## How to test

Each service exposes interactive Swagger docs at `/docs`:

- http://localhost:8001/docs (User Service)
- http://localhost:8002/docs (Flight Service)
- http://localhost:8003/docs (Hotel Service)
- http://localhost:8004/docs (Billing Service)

Or with curl:

```bash
# Sign up
curl -X POST http://localhost:8001/signup \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "123-45-6789", "first_name": "Jane", "last_name": "Doe",
    "address": "123 Main St", "city": "San Jose", "state": "CA",
    "zip_code": "95112", "phone": "408-555-0100",
    "email": "jane@example.com", "password": "hunter2pass"
  }'

# Log in - returns a JWT
curl -X POST http://localhost:8001/login \
  -H "Content-Type: application/json" \
  -d '{"email": "jane@example.com", "password": "hunter2pass"}'

# Use the token from /login on a protected route
curl http://localhost:8001/users/123-45-6789 \
  -H "Authorization: Bearer <token>"

# Search flights
curl "http://localhost:8002/flights?departure_airport=JFK&max_price=500"

# Create a booking (requires a token)
curl -X POST http://localhost:8004/bookings \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "123-45-6789", "booking_type": "flight",
    "item_id": "AA1000", "amount": "349.99", "payment_method": "credit_card"
  }'
```

## Why these design choices

**Why user_id validation uses regex.** `user_id` is required to be an
SSN-formatted string (`###-##-####`). A regex check is the simplest correct
tool for "does this string match a fixed character pattern" - no need for a
full parsing library for a fixed-length, fixed-shape identifier. Validation
runs in `common/validation.py` and is checked *before* any database write,
so a malformed `user_id` fails fast with a specific `400` error instead of
either silently corrupting data (the database has no way to know this
string column is supposed to look like an SSN) or surfacing as a generic
`500` error deep inside a database call.

**How the JWT auth flow works.** `POST /login` verifies the submitted
password against the bcrypt hash stored at signup, then issues a JWT - a
signed token containing the user's `user_id` and a 24-hour expiry, signed
with a secret key (`JWT_SECRET_KEY`) that every service shares via `.env`.
The client stores this token and sends it as
`Authorization: Bearer <token>` on every request to a protected endpoint.
Any service can verify the token's signature and expiry using the shared
secret alone, with no database lookup and no call to User Service - this is
what "stateless auth" means, and it's why the same 4 lines of code
(`common/auth.py`'s `get_current_user`) work identically across all 4
independent services.

**Why booking + billing use a transaction.** `POST /bookings` in Billing
Service inserts a `Booking` row and a `Billing` row together. Both are
added to one SQLAlchemy session and written with a single `db.commit()`
call - not two separate commits wrapped in a try/except. Atomicity comes
from that single shared commit: until it succeeds, MySQL has not durably
written either row, so any failure beforehand leaves the database exactly
as it was. If a booking could be committed independently of its billing
record, a network blip on the second insert would leave a "booking with no
payment" in the database permanently - an inconsistent state a real
booking system cannot tolerate.

**Why CORS is enabled.** Each service adds `CORSMiddleware` with
`allow_origins=["*"]`. Browsers block JavaScript on one origin (e.g. a
plain HTML/JS frontend on a different port, or opened as a local file)
from calling an API on a different origin unless that API explicitly
allows it via response headers. This is permissive on purpose for local
development, where a frontend will call these 4 APIs directly from the
browser; it should be locked down to specific known domains before any
production deployment.

## Project layout

```
travel-booking-system/
  services/
    user_service/       (port 8001)
    flight_service/      (port 8002)
    hotel_service/        (port 8003)
    billing_service/        (port 8004)
  common/
    auth.py             (shared JWT + bcrypt helpers)
    mongo.py            (shared MongoDB connection for reviews)
    validation.py         (shared SSN/zip/state validators, custom exceptions)
  docker-compose.yml
  .env.example
  .gitignore
  seed_data.py
  README.md
```

Each service folder contains: `main.py` (routes), `models.py` (SQLAlchemy
models), `schemas.py` (Pydantic request/response models), `database.py`
(DB session setup), `crud.py` (business logic), `requirements.txt`, and a
`Dockerfile`.
