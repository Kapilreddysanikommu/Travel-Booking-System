"""ai_service: Deals Agent (background scoring) + Concierge Agent (/recommend, added in Part 2)."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from services.ai_service.deals_store import get_snapshot
from services.ai_service.recommender import build_recommendations
from services.ai_service.schemas import DealsSnapshotResponse, RecommendRequest, RecommendResponse
from services.ai_service.scheduler import refresh_deals_once, run_deals_refresh_loop

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Populate the snapshot synchronously before serving traffic, so the
    # first request doesn't race an empty store during the first 60s.
    refresh_deals_once()
    task = asyncio.create_task(run_deals_refresh_loop())
    yield
    task.cancel()


app = FastAPI(title="AI Recommendation Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "ai_service"}


@app.get("/deals", response_model=DealsSnapshotResponse)
def get_deals(top_n: int = Query(default=10, ge=1, le=100)):
    """Debug/inspection endpoint: current deal scores, best deals first."""
    snapshot = get_snapshot()
    return DealsSnapshotResponse(
        last_refreshed=snapshot.last_refreshed,
        flight_deal_count=sum(1 for d in snapshot.flight_deals if d["is_deal"]),
        hotel_deal_count=sum(1 for d in snapshot.hotel_deals if d["is_deal"]),
        top_flight_deals=snapshot.flight_deals[:top_n],
        top_hotel_deals=snapshot.hotel_deals[:top_n],
    )


@app.post("/recommend", response_model=RecommendResponse)
def recommend(request: RecommendRequest):
    snapshot = get_snapshot()
    recommendations, message = build_recommendations(
        flight_deals=snapshot.flight_deals,
        hotel_deals=snapshot.hotel_deals,
        budget=request.budget,
        origin=request.origin,
        destination=request.destination,
        city=request.city,
        start_date=request.start_date,
        end_date=request.end_date,
    )
    return RecommendResponse(recommendations=recommendations, message=message)
