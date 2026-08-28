from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

from .schemas.travel import TravelerProfile, Itinerary, ReplanRequest, DiffExplanation, Place
from .services.ai_service import parse_preferences_llm
from .services.solver import build_itinerary
from .services.replanner import execute_replanning
from .services.places_api import fetch_places_from_google as get_places

app = FastAPI(title="TravelMind API", description="Intelligent Constraint-Aware Travel Planner API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

@app.get("/api/places", response_model=List[Place])
def list_places():
    return get_places()

@app.post("/api/parse-query", response_model=TravelerProfile)
def parse_query(request: QueryRequest):
    try:
        return parse_preferences_llm(request.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-itinerary", response_model=Itinerary)
def generate_itinerary(profile: TravelerProfile):
    if not profile.destination or not profile.destination.strip():
        raise HTTPException(status_code=400, detail="Please choose a destination in India.")
    try:
        return build_itinerary(profile)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/replan")
def replan_itinerary(request: ReplanRequest):
    try:
        new_itinerary, diff = execute_replanning(request)
        return {
            "itinerary": new_itinerary,
            "diff": diff
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
