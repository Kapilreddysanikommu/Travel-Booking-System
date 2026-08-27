"""
Concierge Agent: turns the current deals snapshot into 2-3 flight+hotel
bundles that fit a budget, each with a template-built "why this pick" line.

No LLM call - every explanation is assembled from fields already present on
the scored deal (price, average, rating), which is fast, free, and, unlike
a real LLM call, can never state a number that isn't actually true.
"""

from datetime import date
from decimal import Decimal

# Bounds the flight-candidates x hotel-candidates pairing to a fixed, cheap
# size (at most CANDIDATE_LIMIT^2 pairs) regardless of how many items match
# the filters - with no filters at all that would otherwise be 10000x10000.
CANDIDATE_LIMIT = 25

MAX_RECOMMENDATIONS = 3


def build_recommendations(
    flight_deals: list[dict],
    hotel_deals: list[dict],
    budget: Decimal,
    origin: str | None,
    destination: str | None,
    city: str | None,
    start_date: date | None,
    end_date: date | None,
) -> tuple[list[dict], str | None]:
    """Returns (recommendations, message). message is set when fewer than 2 bundles were found."""
    nights = (end_date - start_date).days if start_date and end_date else 1

    flight_candidates = _filter_flights(flight_deals, origin, destination)[:CANDIDATE_LIMIT]
    hotel_candidates = _filter_hotels(hotel_deals, city)[:CANDIDATE_LIMIT]

    pairs = _affordable_pairs(flight_candidates, hotel_candidates, nights, budget)
    recommendations = _pick_top_distinct(pairs, nights)

    message = None
    if not flight_candidates:
        message = "No flights matched origin/destination - try loosening those filters."
    elif not hotel_candidates:
        message = "No hotels matched that city - try loosening that filter."
    elif not recommendations:
        message = "No flight+hotel combination fit that budget - try raising it."
    elif len(recommendations) < 2:
        message = "Only a limited number of matches fit this budget/filter combination."

    return recommendations, message


def _filter_flights(flight_deals: list[dict], origin: str | None, destination: str | None) -> list[dict]:
    result = flight_deals
    if origin is not None:
        result = [f for f in result if f["departure_airport"].lower() == origin.lower()]
    if destination is not None:
        result = [f for f in result if f["arrival_airport"].lower() == destination.lower()]
    return result


def _filter_hotels(hotel_deals: list[dict], city: str | None) -> list[dict]:
    if city is None:
        return hotel_deals
    return [h for h in hotel_deals if city.lower() in h["city"].lower()]


def _affordable_pairs(
    flight_candidates: list[dict], hotel_candidates: list[dict], nights: int, budget: Decimal
) -> list[dict]:
    """Every flight x hotel combo that fits the budget, ranked by combined deal quality."""
    pairs = []
    for flight in flight_candidates:
        for hotel in hotel_candidates:
            total_cost = flight["price"] + hotel["price_per_night"] * nights
            if total_cost > budget:
                continue
            pairs.append({
                "flight": flight,
                "hotel": hotel,
                "total_cost": total_cost,
                "combined_deal_score": flight["pct_below_avg"] + hotel["pct_below_avg"],
            })

    pairs.sort(key=lambda p: (-p["combined_deal_score"], p["total_cost"]))
    return pairs


def _pick_top_distinct(pairs: list[dict], nights: int) -> list[dict]:
    """
    Take the best-ranked pairs, skipping any that reuse a flight or hotel
    already picked - so 3 recommendations means 3 genuinely different
    options, not the same standout hotel paired with 3 different flights.
    """
    picked = []
    used_flight_ids = set()
    used_hotel_ids = set()

    for pair in pairs:
        flight_id = pair["flight"]["flight_id"]
        hotel_id = pair["hotel"]["hotel_id"]
        if flight_id in used_flight_ids or hotel_id in used_hotel_ids:
            continue

        used_flight_ids.add(flight_id)
        used_hotel_ids.add(hotel_id)
        picked.append({
            "flight": pair["flight"],
            "hotel": pair["hotel"],
            "nights": nights,
            "total_estimated_cost": pair["total_cost"],
            "why_this_pick": _build_why_text(pair["flight"], pair["hotel"], nights),
        })

        if len(picked) == MAX_RECOMMENDATIONS:
            break

    return picked


def _build_why_text(flight: dict, hotel: dict, nights: int) -> str:
    flight_part = _describe_flight_deal(flight)
    hotel_part = _describe_hotel_deal(hotel, nights)
    return f"{flight_part} {hotel_part}"


def _describe_flight_deal(flight: dict) -> str:
    pct = round(flight["pct_below_avg"] * 100)
    route = f"{flight['departure_airport']}-{flight['arrival_airport']}"
    if flight["is_deal"]:
        return f"Flight is {pct}% below the average price for {route} (${flight['price']})."
    return f"Flight is the best available match for {route} at ${flight['price']}, close to the route average."


def _describe_hotel_deal(hotel: dict, nights: int) -> str:
    pct = round(hotel["pct_below_avg"] * 100)
    stars = hotel["star_rating"]
    night_word = "night" if nights == 1 else "nights"
    if hotel["is_deal"]:
        return (
            f"Hotel is {pct}% below the average nightly price in {hotel['city']} "
            f"(${hotel['price_per_night']}/night x {nights} {night_word}), {stars}-star."
        )
    return (
        f"Hotel is the best available match in {hotel['city']} at ${hotel['price_per_night']}/night "
        f"x {nights} {night_word}, {stars}-star."
    )
