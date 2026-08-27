"""hotel_service: search/list hotels, create hotels, and post reviews."""

from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from common.auth import get_current_user
from services.hotel_service import crud
from services.hotel_service.cache import cache_hotel, get_cached_hotel, invalidate_hotel_cache
from services.hotel_service.database import Base, engine, get_db
from services.hotel_service.schemas import (
    HotelCreate,
    HotelResponse,
    HotelUpdate,
    ReviewCreate,
    ReviewResponse,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hotel Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "hotel_service"}


@app.get("/hotels", response_model=list[HotelResponse])
def search_hotels(
    city: Optional[str] = None,
    max_price: Optional[float] = None,
    min_star_rating: Optional[int] = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return crud.list_hotels(db, city, max_price, min_star_rating, limit, offset)


@app.get("/hotels/{hotel_id}", response_model=HotelResponse)
def get_hotel(hotel_id: str, db: Session = Depends(get_db)):
    cached = get_cached_hotel(hotel_id)
    if cached is not None:
        return cached

    hotel = crud.get_hotel_by_id(db, hotel_id)
    if hotel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found")

    response = HotelResponse.model_validate(hotel)
    cache_hotel(hotel_id, response)
    return response


@app.post("/hotels", response_model=HotelResponse, status_code=status.HTTP_201_CREATED)
def create_hotel(
    hotel_data: HotelCreate,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    return crud.create_hotel(db, hotel_data)


@app.put("/hotels/{hotel_id}", response_model=HotelResponse)
def update_hotel(
    hotel_id: str,
    hotel_data: HotelUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    hotel = crud.update_hotel(db, hotel_id, hotel_data)
    if hotel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found")

    invalidate_hotel_cache(hotel_id)
    return hotel


@app.post(
    "/reviews/hotels/{hotel_id}",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_hotel_review(
    hotel_id: str,
    review_data: ReviewCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    review = crud.create_review(db, hotel_id, user_id, review_data)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found")
    return review
