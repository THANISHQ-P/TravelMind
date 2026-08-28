import json
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
from ..schemas.travel import Place
from ..config import settings
from .places_data import get_places as get_cached_places

logger = logging.getLogger("travelmind.places_api")

def map_google_types_to_categories(types: List[str]) -> List[str]:
    categories = []
    # Keywords for history
    history_types = {"museum", "landmark", "historical_landmark", "tourist_attraction", "place_of_worship", "church", "hindu_temple"}
    # Keywords for local food
    food_types = {"restaurant", "food", "cafe", "bar", "meal_takeaway", "brewery"}
    # Keywords for nature
    nature_types = {"park", "zoo", "garden", "amusement_park"}

    for t in types:
        if t in history_types:
            categories.append("history")
        if t in food_types:
            categories.append("local food")
        if t in nature_types:
            categories.append("nature")
            
    # Default to history if empty
    return list(set(categories)) if categories else ["history"]

def parse_opening_hours(hours_data: Optional[Dict[str, Any]]) -> Dict[str, float]:
    # Default hours
    default_hours = {"open": 9.0, "close": 18.0}
    if not hours_data or "periods" not in hours_data:
        return default_hours
    
    # Try to extract from the first period
    try:
        periods = hours_data["periods"]
        if periods:
            open_time = periods[0].get("open", {}).get("time", "0900")
            close_time = periods[0].get("close", {}).get("time", "1800")
            
            open_h = int(open_time[:2]) + int(open_time[2:]) / 60.0
            close_h = int(close_time[:2]) + int(close_time[2:]) / 60.0
            return {"open": open_h, "close": close_h}
    except Exception:
        pass
        
    return default_hours

def fetch_places_from_google() -> List[Place]:
    if not settings.PLACES_API_KEY:
        logger.info("Google Places API key is missing. Using cached India-wide data.")
        return get_cached_places()

    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.PLACES_API_KEY,
        "X-Goog-FieldMask": "places.id,places.displayName,places.editorialSummary,places.location,places.rating,places.userRatingCount,places.priceLevel,places.regularOpeningHours,places.types"
    }

    # Search for tourist hotspots across India rather than a single city
    queries = ["top tourist attractions in India", "famous food destinations in India"]
    google_places = []

    for q in queries:
        body = {
            "textQuery": q,
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": 22.9734,
                        "longitude": 78.6569
                    },
                    "radius": 3000000.0
                }
            }
        }
        
        try:
            req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=5) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                if "places" in res_data:
                    google_places.extend(res_data["places"])
        except urllib.error.URLError as e:
            logger.error(f"Google Places API request failed: {e}. Falling back.")
            return get_cached_places()
        except Exception as e:
            logger.error(f"Error parsing Google Places response: {e}. Falling back.")
            return get_cached_places()

    if not google_places:
        return get_cached_places()

    # Normalize response into standard Place model
    normalized_places: List[Place] = []
    seen_ids = set()

    for p in google_places:
        place_id = p.get("id")
        if not place_id or place_id in seen_ids:
            continue
        seen_ids.add(place_id)

        name = p.get("displayName", {}).get("text", "Unknown Spot")
        description = p.get("editorialSummary", {}).get("text", "A popular destination in India.")
        
        loc = p.get("location", {})
        lat = loc.get("latitude", 22.9734)
        lng = loc.get("longitude", 78.6569)
        
        types = p.get("types", [])
        categories = map_google_types_to_categories(types)
        
        hours = parse_opening_hours(p.get("regularOpeningHours"))
        
        # Estimate spend based on Google price level
        price_level = p.get("priceLevel", "PRICE_LEVEL_INEXPENSIVE")
        spend_map = {
            "PRICE_LEVEL_FREE": 0.0,
            "PRICE_LEVEL_INEXPENSIVE": 100.0,
            "PRICE_LEVEL_MODERATE": 300.0,
            "PRICE_LEVEL_EXPENSIVE": 600.0,
            "PRICE_LEVEL_VERY_EXPENSIVE": 1200.0
        }
        average_spend = spend_map.get(price_level, 200.0)
        
        # Default durations based on categories
        duration = 90
        if "local food" in categories:
            duration = 60
        elif "nature" in categories:
            duration = 120

        # Walking level heuristic
        walking = "little"
        if "nature" in categories:
            walking = "active"
        elif "museum" in types or "zoo" in types:
            walking = "moderate"

        normalized_places.append(Place(
            id=place_id,
            name=name,
            description=description,
            lat=lat,
            lng=lng,
            categories=categories,
            opening_hours=hours,
            average_spend=average_spend,
            duration_mins=duration,
            walking_level=walking,
            rating=p.get("rating", 4.0),
            user_ratings_total=p.get("userRatingCount", 100),
            weather_suitability="indoor" if "local food" in categories or "museum" in types else "both"
        ))

    return normalized_places
