"""
Deals Agent: scores flights and hotels against the average price for
comparable items, and flags anything DEAL_THRESHOLD or more below that
average as a deal.

Reads directly from the flights/hotels tables that flight_service and
hotel_service own, via raw SQL. This is a deliberate exception to the
"a service only touches its own tables" boundary used elsewhere in this
project: a recommendation service inherently needs data from both, and one
read-only query per table here is simpler and cheaper than fanning out to
two other services' HTTP APIs just to compute an aggregate.
"""

from decimal import Decimal
from typing import Callable

from sqlalchemy import text
from sqlalchemy.engine import Row
from sqlalchemy.orm import Session

# 15% below the group average is the line for calling something a "deal".
DEAL_THRESHOLD = Decimal("0.15")


def compute_flight_deals(db: Session) -> list[dict]:
    """Score every flight against the average price for its route (departure -> arrival)."""
    rows = db.execute(
        text(
            """
            SELECT flight_id, airline, departure_airport, arrival_airport,
                   departure_datetime, arrival_datetime, flight_class, price
            FROM flights
            """
        )
    ).mappings().all()

    return _score_group(
        rows,
        group_key=lambda r: (r["departure_airport"], r["arrival_airport"]),
        price_key="price",
    )


def compute_hotel_deals(db: Session) -> list[dict]:
    """Score every hotel against the average nightly price for its city."""
    rows = db.execute(
        text(
            """
            SELECT hotel_id, name, city, state, star_rating, room_type, price_per_night
            FROM hotels
            """
        )
    ).mappings().all()

    return _score_group(
        rows,
        group_key=lambda r: r["city"],
        price_key="price_per_night",
    )


def _score_group(rows: list[Row], group_key: Callable[[Row], object], price_key: str) -> list[dict]:
    """
    Group rows by group_key, compute each group's average price, then attach
    a deal score to every row relative to its own group's average.

    Two passes over the rows - one to sum price per group, one to score each
    row against the now-known average - keeps memory at O(groups) instead of
    building a second full copy of the rows to compute the averages from.
    """
    sums: dict[object, Decimal] = {}
    counts: dict[object, int] = {}
    for row in rows:
        key = group_key(row)
        sums[key] = sums.get(key, Decimal("0")) + row[price_key]
        counts[key] = counts.get(key, 0) + 1

    averages = {key: sums[key] / counts[key] for key in sums}

    scored = []
    for row in rows:
        key = group_key(row)
        avg = averages[key]
        price = row[price_key]
        pct_below_avg = (avg - price) / avg if avg > 0 else Decimal("0")
        item = dict(row)
        item["group_average_price"] = avg
        item["pct_below_avg"] = pct_below_avg
        item["is_deal"] = pct_below_avg >= DEAL_THRESHOLD
        scored.append(item)

    scored.sort(key=lambda item: item["pct_below_avg"], reverse=True)
    return scored
