# Travel Booking System

A Python/FastAPI backend split into 6 independent microservices, sharing one
MySQL instance (separate tables per service), one MongoDB instance (for
reviews), Kafka (for booking events), and Redis (for cache-aside lookups and
the AI service's deal scores).

- User Service — port 8001
- Flight Service — port 8002
- Hotel Service — port 8003
- Billing Service — port 8004
- Notification Service — port 8005 (Kafka consumer, no routes beyond `/health`)
- AI Recommendation Service — port 8006

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
- http://localhost:8006/docs (AI Recommendation Service)

(Notification Service exposes no Swagger docs worth visiting - it's a
background Kafka consumer with only `/health`.)

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

## AI Recommendation Service

Two agents inside `services/ai_service/`, both reading the same MySQL
`flights`/`hotels` tables that Flight Service and Hotel Service own:

**Deals Agent** (background worker, `deals_agent.py` + `scheduler.py`) runs
every 60 seconds and scores every flight against the average price for its
route (`departure_airport` + `arrival_airport`) and every hotel against the
average nightly price for its `city`. Anything 15%+ below its group's
average is flagged `is_deal: true`. Scores are kept in an in-memory
snapshot (not Redis) - the whole snapshot is recomputed from scratch every
cycle, only this one process ever reads it, and Python's reference
reassignment is atomic, so there's nothing a persistent cache would buy
here. Inspect the current snapshot directly:

```bash
curl "http://localhost:8006/deals?top_n=5"
```

**Concierge Agent** (`recommender.py`, exposed as `POST /recommend`) pairs
flights and hotels from that snapshot into bundles that fit a budget,
ranked by combined deal quality, returning up to 3 distinct bundles (no
repeated flight or hotel across picks). `origin`/`destination` filter by
airport code and `city` filters hotels by name - the two are applied
independently, since the seed data doesn't link airport codes to the
random city names hotels get, so there's no "same destination" to match
flights and hotels against. `why_this_pick` is built entirely from
template text over real fields (price, average, star rating) - no LLM
call, so it can't state a number that isn't true.

```bash
curl -X POST http://localhost:8006/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "budget": 300,
    "start_date": "2026-09-01",
    "end_date": "2026-09-04"
  }'
```

```json
{
  "recommendations": [
    {
      "flight": {
        "flight_id": "B68118", "airline": "JetBlue Airways",
        "departure_airport": "SLC", "arrival_airport": "TPA",
        "price": "50.32", "group_average_price": "1075.24",
        "pct_below_avg": "0.9532", "is_deal": true
      },
      "hotel": {
        "hotel_id": "HT101025", "name": "Short-Soto Hotel",
        "city": "Wilsonmouth", "star_rating": 5,
        "price_per_night": "50.04", "group_average_price": "333.71",
        "pct_below_avg": "0.8500", "is_deal": true
      },
      "nights": 3,
      "total_estimated_cost": "200.44",
      "why_this_pick": "Flight is 95% below the average price for SLC-TPA ($50.32). Hotel is 85% below the average nightly price in Wilsonmouth ($50.04/night x 3 nights), 5-star."
    }
  ],
  "message": null
}
```

Exact ids/prices above came from one run against seeded data and will
differ after any reseed - `seed_data.py` generates prices and cities
randomly. Add `origin`, `destination`, and/or `city` to narrow the search;
if nothing fits, `recommendations` is `[]` and `message` explains why
(unmatched filter vs. budget too low).

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
    notification_service/     (port 8005)
    ai_service/                 (port 8006)
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
