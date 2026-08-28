import math
from typing import List, Dict, Set, Optional
from ..schemas.travel import TravelerProfile, Place, Itinerary, ItineraryDay, ItineraryActivity, ItineraryValidationReport
from .places_api import fetch_places_from_google as get_places

DESTINATION_COORDS = {
    "bengaluru, karnataka, india": (12.9716, 77.5946),
    "bengaluru, karnataka": (12.9716, 77.5946),
    "bangalore, karnataka, india": (12.9716, 77.5946),
    "bangalore, karnataka": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
    "bengaluru": (12.9716, 77.5946),
    "munnar, kerala, india": (10.0889, 77.0595),
    "munnar, kerala": (10.0889, 77.0595),
    "munnar": (10.0889, 77.0595),
    "vagamon, kerala, india": (9.6402, 76.8741),
    "vagamon, kerala": (9.6402, 76.8741),
    "vagamon": (9.6402, 76.8741),
    "ooty, tamil nadu, india": (11.4064, 76.6932),
    "ooty, tamil nadu": (11.4064, 76.6932),
    "ooty": (11.4064, 76.6932),
    "pondicherry, puducherry, india": (11.9416, 79.8083),
    "pondicherry, puducherry": (11.9416, 79.8083),
    "pondicherry": (11.9416, 79.8083),
    "goa, india": (15.2993, 74.1239),
    "goa": (15.2993, 74.1239),
    "jaipur, rajasthan, india": (26.9124, 75.7873),
    "jaipur, rajasthan": (26.9124, 75.7873),
    "jaipur": (26.9124, 75.7873),
    "manali, himachal pradesh, india": (32.2432, 77.1892),
    "manali, himachal pradesh": (32.2432, 77.1892),
    "manali": (32.2432, 77.1892),
    "wayanad, kerala, india": (11.6854, 76.1320),
    "wayanad, kerala": (11.6854, 76.1320),
    "wayanad": (11.6854, 76.1320),
    "coorg, karnataka, india": (12.4244, 75.7382),
    "coorg, karnataka": (12.4244, 75.7382),
    "coorg": (12.4244, 75.7382),
    "mumbai, maharashtra, india": (19.0760, 72.8777),
    "mumbai, maharashtra": (19.0760, 72.8777),
    "mumbai": (19.0760, 72.8777),
    "delhi, india": (28.6139, 77.2090),
    "delhi": (28.6139, 77.2090),
    "chennai, tamil nadu, india": (13.0827, 80.2707),
    "chennai, tamil nadu": (13.0827, 80.2707),
    "chennai": (13.0827, 80.2707),
    "kochi, kerala, india": (9.9312, 76.2673),
    "kochi, kerala": (9.9312, 76.2673),
    "kochi": (9.9312, 76.2673),
    "alleppey, kerala, india": (9.4981, 76.3384),
    "alleppey, kerala": (9.4981, 76.3384),
    "alleppey": (9.4981, 76.3384),
    "kodaikanal, tamil nadu, india": (10.2381, 77.4892),
    "kodaikanal, tamil nadu": (10.2381, 77.4892),
    "kodaikanal": (10.2381, 77.4892)
}


def get_destination_coords(destination: str) -> Optional[tuple[float, float]]:
    if not destination:
        return None

    normalized = destination.strip().lower().replace("  ", " ")
    normalized = normalized.replace(";", ",")
    normalized = normalized.replace("-", " ")
    normalized = normalized.replace("  ", " ")
    normalized = normalized.strip(", ")
    if normalized.endswith(", india"):
        normalized = normalized[:-len(", india")].strip()
    if normalized in DESTINATION_COORDS:
        return DESTINATION_COORDS[normalized]

    for key in DESTINATION_COORDS:
        if normalized == key or normalized.startswith(key + ",") or key.startswith(normalized + ","):
            return DESTINATION_COORDS[key]

    return None


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    # Radius of the Earth in km
    R = 6371.0
    
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return round(R * c, 2)


def infer_place_state(place: Place) -> str:
    pool = f"{place.id} {place.name} {place.description}".lower()
    for state_name, tokens in {
        "andhra pradesh": ["andhra", "tirumala"],
        "arunachal pradesh": ["arunachal", "tawang"],
        "assam": ["assam", "kaziranga"],
        "bihar": ["bihar", "mahabodhi"],
        "chhattisgarh": ["chhattisgarh", "chitrakote"],
        "goa": ["goa", "baga"],
        "gujarat": ["gujarat", "modhera"],
        "haryana": ["haryana", "surajkund"],
        "himachal pradesh": ["himachal", "shimla", "manali"],
        "jharkhand": ["jharkhand", "hundru"],
        "karnataka": ["karnataka", "mysore", "mysuru", "hampi", "coorg", "bangalore", "bengaluru", "cubbon", "lalbagh"],
        "kerala": ["kerala", "munnar", "vagamon", "wayanad", "kochi", "alleppey", "alappuzha", "varkala", "thekkady"],
        "madhya pradesh": ["madhya", "khajuraho", "bhopal"],
        "maharashtra": ["maharashtra", "gateway", "mumbai"],
        "manipur": ["manipur", "loktak"],
        "meghalaya": ["meghalaya", "shillong"],
        "mizoram": ["mizoram", "reiek"],
        "nagaland": ["nagaland", "kohima"],
        "odisha": ["odisha", "konark"],
        "punjab": ["punjab", "golden temple", "amritsar"],
        "rajasthan": ["rajasthan", "amber", "jaipur", "udaipur", "jaisalmer"],
        "sikkim": ["sikkim", "tsomgo", "gangtok"],
        "tamil nadu": ["tamil", "meenakshi", "ooty", "kodaikanal"],
        "telangana": ["telangana", "charminar", "hyderabad"],
        "tripura": ["tripura", "ujjayanta"],
        "uttar pradesh": ["uttar", "taj", "varanasi"],
        "uttarakhand": ["uttarakhand", "nainital", "rishikesh"],
        "west bengal": ["west bengal", "darjeeling", "kolkata"],
        "andaman and nicobar islands": ["andaman", "nicobar"],
        "lakshadweep": ["lakshadweep"],
        "puducherry": ["pondicherry", "puducherry"],
        "delhi": ["delhi"],
        "uttar pradesh": ["uttar", "taj", "varanasi"],
        "sikkim": ["sikkim", "gangtok"],
    }.items():
        if any(token in pool for token in tokens):
            return state_name
    return ""

def calculate_travel_time_mins(distance_km: float) -> int:
    # Average speed in Bengaluru traffic is about 15 km/h
    speed_kmh = 15.0
    time_hours = distance_km / speed_kmh
    time_mins = int(time_hours * 60)
    # Add a minimum buffer of 10 minutes for traffic/parking
    return max(10, time_mins)

def decimal_to_time_str(decimal_hours: float) -> str:
    hours = int(decimal_hours)
    minutes = int(round((decimal_hours - hours) * 60))
    if minutes == 60:
        hours += 1
        minutes = 0
    return f"{hours:02d}:{minutes:02d}"

def time_str_to_decimal(time_str: str) -> float:
    parts = time_str.split(":")
    return int(parts[0]) + int(parts[1]) / 60.0

def build_itinerary(profile: TravelerProfile, rain_mode: bool = False) -> Itinerary:
    places = get_places()
    destination_coords = get_destination_coords(profile.destination or "")
    destination_key = (profile.destination or "").strip().lower()
    destination_state = (profile.state or "").strip().lower()
    destination_radius_km = 300.0
    if destination_key.startswith("goa"):
        destination_radius_km = 220.0
    elif destination_key.startswith("jaipur"):
        destination_radius_km = 260.0
    elif destination_key.startswith("manali"):
        destination_radius_km = 240.0
    elif destination_key.startswith("munnar") or destination_key.startswith("vagamon") or destination_key.startswith("ooty") or destination_key.startswith("coorg") or destination_key.startswith("wayanad"):
        destination_radius_km = 180.0
    
    # 1. Filter places based on constraints
    filtered_places: List[Place] = []
    strict_state_required = bool(destination_state)
    strict_walking_required = profile.walking_limit == "little"
    for p in places:
        inferred_state = (infer_place_state(p) or "").lower()
        state_ok = True
        if strict_state_required and inferred_state and inferred_state != destination_state:
            state_ok = False

        distance_ok = True
        if destination_coords:
            place_distance = haversine_distance(destination_coords[0], destination_coords[1], p.lat, p.lng)
            if place_distance > destination_radius_km and p.id not in profile.locked_places:
                distance_ok = False

        walking_ok = True
        if strict_walking_required and p.walking_level == "active" and p.id not in profile.locked_places:
            walking_ok = False

        # Weather constraint (rain)
        weather_ok = True
        if rain_mode and p.weather_suitability == "outdoor":
            if p.id not in profile.locked_places:
                weather_ok = False

        if state_ok and distance_ok and walking_ok and weather_ok:
            filtered_places.append(p)

    # If strict filters eliminate everything, relax them just enough for a valid destination-focused plan.
    if not filtered_places and destination_state:
        filtered_places = []
        for p in places:
            inferred_state = (infer_place_state(p) or "").lower()
            if destination_state and inferred_state and inferred_state != destination_state and p.id not in profile.locked_places:
                continue
            if destination_coords:
                place_distance = haversine_distance(destination_coords[0], destination_coords[1], p.lat, p.lng)
                if place_distance > destination_radius_km and p.id not in profile.locked_places:
                    continue
            if rain_mode and p.weather_suitability == "outdoor" and p.id not in profile.locked_places:
                continue
            filtered_places.append(p)

    if not filtered_places and destination_coords:
        filtered_places = [p for p in places if p.id not in profile.locked_places and haversine_distance(destination_coords[0], destination_coords[1], p.lat, p.lng) <= destination_radius_km * 2]

    if not filtered_places:
        filtered_places = [p for p in places if p.id not in profile.locked_places]

    # 2. Score candidates (locked places get huge boost, others based on category match + rating)
    scored_places = []
    for p in filtered_places:
        category_match = sum(1 for c in p.categories if c in profile.categories)
        score = p.rating * (1.0 + 0.5 * category_match)
        if p.id in profile.locked_places:
            score += 1000.0 # Force inclusion
        scored_places.append((score, p))
    
    # Sort descending by score
    scored_places.sort(key=lambda x: x[0], reverse=True)
    candidate_sights = [p for _, p in scored_places if "local food" not in p.categories or any(c in p.categories for c in ["history", "nature"])]
    candidate_food = [p for _, p in scored_places if "local food" in p.categories]

    # Starting coordinates follow the selected destination to keep all activities centered on one region
    current_lat, current_lng = destination_coords if destination_coords else (22.9734, 78.6569)
    
    used_place_ids: Set[str] = set()
    days: List[ItineraryDay] = []
    total_cost = 0.0
    
    start_hour = time_str_to_decimal(profile.starting_time)
    
    # Target slots based on pace
    # slow: 1 sight, 1 food, 1 sight (max 3 spots)
    # balanced: 2 sights, 1 lunch, 1 sight, 1 dinner (max 5 spots)
    # fast: 3 sights, 1 lunch, 2 sights, 1 dinner (max 7 spots)
    
    for d in range(1, profile.num_days + 1):
        day_activities: List[ItineraryActivity] = []
        current_time = start_hour
        day_spend = 0.0
        day_travel_time = 0
        
        # We define a day schedule draft
        # Each day we try to select places sequentially that are open and match travel times
        slots = []
        if profile.pace == "slow":
            slots = ["morning_sight", "lunch", "afternoon_sight"]
        elif profile.pace == "balanced":
            slots = ["morning_sight", "lunch", "afternoon_sight", "evening_sight"]
        else: # fast
            slots = ["morning_sight", "morning_sight_2", "lunch", "afternoon_sight", "evening_sight", "dinner"]
            
        day_used_place_ids: Set[str] = set()
        
        for slot in slots:
            is_food_slot = (slot in ["lunch", "dinner"])
            target_list = candidate_food if is_food_slot else candidate_sights
            
            selected_place: Optional[Place] = None
            best_travel_time = 9999
            best_distance = 0.0
            
            # Check if all spots in target list are already used overall
            all_used_overall = all(p.id in used_place_ids for p in target_list)
            
            for p in target_list:
                # Hard rules:
                # 1. Never visit the same place twice on the same day.
                if p.id in day_used_place_ids:
                    continue
                # 2. For sights, if we haven't exhausted the catalog, don't repeat them.
                # If we have exhausted the catalog, we can reuse.
                if not is_food_slot and not all_used_overall:
                    if p.id in used_place_ids:
                        continue
                # 3. For food, we allow repeating on different days so that we don't starve.
                
                # Check opening hours
                open_h = p.opening_hours["open"]
                close_h = p.opening_hours["close"]
                
                dist = haversine_distance(current_lat, current_lng, p.lat, p.lng)
                travel_m = calculate_travel_time_mins(dist)
                arrival_t = current_time + (travel_m / 60.0)
                departure_t = arrival_t + (p.duration_mins / 60.0)
                
                # Check if it fits opening hours
                if arrival_t >= open_h and departure_t <= close_h:
                    # Budget limit check (prevent planning if we exceed the budget cap drastically)
                    if total_cost + day_spend + p.average_spend <= profile.budget:
                        selected_place = p
                        best_travel_time = travel_m
                        best_distance = dist
                        break
            
            if selected_place:
                used_place_ids.add(selected_place.id)
                day_used_place_ids.add(selected_place.id)
                arrival_hour = current_time + (best_travel_time / 60.0)
                departure_hour = arrival_hour + (selected_place.duration_mins / 60.0)
                
                activity = ItineraryActivity(
                    place=selected_place,
                    arrival_time=decimal_to_time_str(arrival_hour),
                    departure_time=decimal_to_time_str(departure_hour),
                    activity_cost=selected_place.average_spend,
                    travel_time_mins=best_travel_time,
                    travel_distance_km=best_distance
                )
                day_activities.append(activity)
                
                day_spend += selected_place.average_spend
                day_travel_time += best_travel_time
                current_time = departure_hour
                current_lat, current_lng = selected_place.lat, selected_place.lng
            else:
                # If no matching place is found, we skip or advance time slightly (e.g. if we are waiting for lunch)
                if is_food_slot:
                    current_time += 1.0 # advance 1 hour for placeholder food
                    
        # Compute walking level for the day
        has_active = any(act.place.walking_level == "active" for act in day_activities)
        has_mod = any(act.place.walking_level == "moderate" for act in day_activities)
        if has_active:
            day_walking = "active"
        elif has_mod:
            day_walking = "moderate"
        else:
            day_walking = "little"
            
        days.append(ItineraryDay(
            day_number=d,
            activities=day_activities,
            total_spend=day_spend,
            total_travel_time_mins=day_travel_time,
            total_walking_level=day_walking
        ))
        total_cost += day_spend

    # Determine overall walking score
    has_active_day = any(d.total_walking_level == "active" for d in days)
    has_mod_day = any(d.total_walking_level == "moderate" for d in days)
    overall_walking = "active" if has_active_day else ("moderate" if has_mod_day else "little")

    itinerary = Itinerary(
        version=1,
        days=days,
        total_cost=total_cost,
        total_walking_score=overall_walking,
        explanation="Generated based on preferences."
    )
    
    # Run validation immediately
    from .validator import validate_itinerary
    itinerary.validity_report = validate_itinerary(itinerary, profile)
    
    return itinerary
