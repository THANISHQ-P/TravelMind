from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class TravelerProfile(BaseModel):
    destination: str = Field(default="")
    state: str = Field(default="")
    country: str = Field(default="India")
    num_days: int = Field(default=3, ge=1, le=7)
    budget: float = Field(default=12000.0, ge=0.0)
    categories: List[str] = Field(default_factory=lambda: ["history", "local food", "nature"])
    pace: str = Field(default="balanced")  # slow, balanced, fast
    walking_limit: str = Field(default="little")  # little, moderate, active
    starting_time: str = Field(default="09:00")  # HH:MM format
    locked_places: List[str] = Field(default_factory=list)  # place IDs that must be included

class Place(BaseModel):
    id: str
    name: str
    description: str
    lat: float
    lng: float
    categories: List[str]
    opening_hours: Dict[str, float]  # e.g., {"open": 9.0, "close": 17.5}
    average_spend: float
    duration_mins: int
    walking_level: str  # little, moderate, active
    rating: float
    user_ratings_total: int
    weather_suitability: str  # indoor, outdoor, both

class ItineraryActivity(BaseModel):
    place: Place
    arrival_time: str  # HH:MM
    departure_time: str  # HH:MM
    activity_cost: float
    travel_time_mins: int
    travel_distance_km: float

class ItineraryDay(BaseModel):
    day_number: int
    activities: List[ItineraryActivity] = Field(default_factory=list)
    total_spend: float = 0.0
    total_travel_time_mins: int = 0
    total_walking_level: str = "little"

class ItineraryValidationReport(BaseModel):
    is_valid: bool
    budget_ok: bool
    time_overlap_free: bool
    opening_hours_ok: bool
    walking_limit_ok: bool
    warnings: List[str] = Field(default_factory=list)

class Itinerary(BaseModel):
    version: int = 1
    days: List[ItineraryDay] = Field(default_factory=list)
    total_cost: float = 0.0
    total_walking_score: str = "little"
    validity_report: Optional[ItineraryValidationReport] = None
    explanation: str = ""

class ReplanRequest(BaseModel):
    current_itinerary: Itinerary
    profile: TravelerProfile
    trigger: str  # e.g., "rain", "budget_cut", "less_walking", "later_start", "add_place", "close_place"
    trigger_value: Optional[str] = None  # context/extra parameter for the trigger

class DiffExplanation(BaseModel):
    before_version: int
    after_version: int
    changes: List[str]
    reasoning: str
