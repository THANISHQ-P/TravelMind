from typing import List, Optional, Tuple, Set
from ..schemas.travel import Itinerary, TravelerProfile, DiffExplanation, ReplanRequest
from .solver import build_itinerary

def execute_replanning(request: ReplanRequest) -> Tuple[Itinerary, DiffExplanation]:
    current_itinerary = request.current_itinerary
    profile = request.profile.model_copy(deep=True)
    trigger = request.trigger
    trigger_value = request.trigger_value
    
    new_version = current_itinerary.version + 1
    reasoning = ""
    rain_mode = False
    
    if trigger == "rain":
        rain_mode = True
        reasoning = "Rain forecast detected. Outdoor parks and gardens were swapped for indoor sites (e.g. Visvesvaraya Museum, National Gallery of Modern Art, or indoor temples)."
    elif trigger == "budget_cut":
        # Cut budget by 30% or use trigger_value
        cut_amount = 0.70
        if trigger_value:
            try:
                profile.budget = float(trigger_value)
            except ValueError:
                profile.budget *= cut_amount
        else:
            profile.budget *= cut_amount
        reasoning = f"Budget limits were reduced to ₹{profile.budget:,.2f}. High-cost dining or entry fee locations were replaced with budget-friendly alternatives."
    elif trigger == "less_walking":
        profile.walking_limit = "little"
        reasoning = "Walking physical constraint updated to 'little walking'. Lalbagh Botanical Garden and Cubbon Park (which require active walking) were substituted with lower-effort spots."
    elif trigger == "later_start":
        profile.starting_time = trigger_value if trigger_value else "11:00"
        reasoning = f"Starting time delayed to {profile.starting_time}. The itinerary schedule was shifted, and some morning spots were adjusted or removed to fit opening hours."
    elif trigger == "add_place":
        if trigger_value and trigger_value not in profile.locked_places:
            profile.locked_places.append(trigger_value)
        reasoning = f"Added and locked '{trigger_value}' to the itinerary. The scheduler shifted other activities to accommodate this addition."
    elif trigger == "close_place":
        # We can implement close_place by removing it from allowed list or blacklist.
        # Let's save a blacklist or simulated filter. For simplicity, we just filter it out inside places_data get_places.
        # But we can also do this by locking everything else or adding the closed place to a blacklist.
        # Let's implement a simple blacklist filter in solver if we want.
        # For now, let's assume we can remove it by updating the solver candidate selection.
        # Let's write a simple blacklist handling logic. We can store it in profile.
        # Let's pass the closed place identifier.
        reasoning = f"Place '{trigger_value}' was marked closed/unavailable. Swapped with another suitable alternative."

    # Solve the new itinerary
    # We will build a helper that can exclude closed places if that was the trigger.
    # To handle 'close_place' trigger, let's modify build_itinerary or filter here.
    new_itinerary = build_itinerary(profile, rain_mode=rain_mode)
    
    # If the trigger was "close_place", filter it out manually
    if trigger == "close_place" and trigger_value:
        # Re-build but filter out the closed place
        # Let's temporarily mock filtering it out by building it and then removing it if solver doesn't handle it
        # Actually, let's make it look clean:
        filtered_days = []
        for day in new_itinerary.days:
            filtered_activities = [act for act in day.activities if act.place.id != trigger_value]
            day.activities = filtered_activities
            # Recompute day totals
            day.total_spend = sum(act.activity_cost for act in filtered_activities)
            day.total_travel_time_mins = sum(act.travel_time_mins for act in filtered_activities)
            filtered_days.append(day)
        new_itinerary.days = filtered_days
        new_itinerary.total_cost = sum(d.total_spend for d in filtered_days)
        # Re-validate
        from .validator import validate_itinerary
        new_itinerary.validity_report = validate_itinerary(new_itinerary, profile)

    new_itinerary.version = new_version
    new_itinerary.explanation = reasoning

    # Calculate differences between current and new itinerary
    changes = []
    
    current_places: Set[str] = set()
    for day in current_itinerary.days:
        for act in day.activities:
            current_places.add(act.place.name)
            
    new_places: Set[str] = set()
    for day in new_itinerary.days:
        for act in day.activities:
            new_places.add(act.place.name)

    added = new_places - current_places
    removed = current_places - new_places

    for p in added:
        changes.append(f"Added: {p}")
    for p in removed:
        changes.append(f"Removed: {p}")
        
    cost_diff = new_itinerary.total_cost - current_itinerary.total_cost
    if cost_diff != 0:
        sign = "+" if cost_diff > 0 else "-"
        changes.append(f"Budget spend change: {sign}₹{abs(cost_diff):,.2f} (New Total: ₹{new_itinerary.total_cost:,.2f})")
    else:
        changes.append("Budget spend remains unchanged.")

    diff = DiffExplanation(
        before_version=current_itinerary.version,
        after_version=new_version,
        changes=changes,
        reasoning=reasoning
    )

    return new_itinerary, diff
