"""flight_service: search/list flights, create flights, and post reviews."""

from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from common.auth import get_current_user
from services.flight_service import crud
from services.flight_service.cache import cache_flight, get_cached_flight, invalidate_flight_cache
from services.flight_service.database import Base, engine, get_db
from services.flight_service.schemas import (
    FlightCreate,
    FlightResponse,
    FlightUpdate,
    ReviewCreate,
    ReviewResponse,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Flight Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "flight_service"}


@app.get("/flights", response_model=list[FlightResponse])
def search_flights(
    departure_airport: Optional[str] = None,
    arrival_airport: Optional[str] = None,
    max_price: Optional[float] = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return crud.list_flights(db, departure_airport, arrival_airport, max_price, limit, offset)


@app.get("/flights/{flight_id}", response_model=FlightResponse)
def get_flight(flight_id: str, db: Session = Depends(get_db)):
    cached = get_cached_flight(flight_id)
    if cached is not None:
        return cached

    flight = crud.get_flight_by_id(db, flight_id)
    if flight is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flight not found")

    response = FlightResponse.model_validate(flight)
    cache_flight(flight_id, response)
    return response


@app.post("/flights", response_model=FlightResponse, status_code=status.HTTP_201_CREATED)
def create_flight(
    flight_data: FlightCreate,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    return crud.create_flight(db, flight_data)


@app.put("/flights/{flight_id}", response_model=FlightResponse)
def update_flight(
    flight_id: str,
    flight_data: FlightUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    flight = crud.update_flight(db, flight_id, flight_data)
    if flight is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flight not found")

    # Delete rather than overwrite with the new value: simpler, and it
    # guarantees the next GET is a genuine miss that reloads from MySQL and
    # re-caches the fresh row - no window where cache and DB could disagree.
    invalidate_flight_cache(flight_id)
    return flight


@app.post(
    "/reviews/flights/{flight_id}",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_flight_review(
    flight_id: str,
    review_data: ReviewCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    review = crud.create_review(db, flight_id, user_id, review_data)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flight not found")
    return review
