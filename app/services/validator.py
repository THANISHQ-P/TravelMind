from typing import List
from ..schemas.travel import Itinerary, TravelerProfile, ItineraryValidationReport, ItineraryActivity
from .solver import time_str_to_decimal

def validate_itinerary(itinerary: Itinerary, profile: TravelerProfile) -> ItineraryValidationReport:
    warnings: List[str] = []
    budget_ok = True
    time_overlap_free = True
    opening_hours_ok = True
    walking_limit_ok = True

    # 1. Budget check
    if itinerary.total_cost > profile.budget:
        budget_ok = False
        warnings.append(f"Total cost (₹{itinerary.total_cost:,.2f}) exceeds your budget limit of ₹{profile.budget:,.2f}.")

    # Iterate through days
    for day in itinerary.days:
        activities: List[ItineraryActivity] = day.activities
        
        # 2. Time overlaps & sequential check
        for i in range(len(activities)):
            act = activities[i]
            arr = time_str_to_decimal(act.arrival_time)
            dep = time_str_to_decimal(act.departure_time)
            
            # Check duration is correct
            duration = dep - arr
            if duration <= 0:
                time_overlap_free = False
                warnings.append(f"Day {day.day_number}: Activity at {act.place.name} has negative or zero duration.")
            
            # Check overlap with subsequent activity
            if i < len(activities) - 1:
                next_act = activities[i+1]
                next_arr = time_str_to_decimal(next_act.arrival_time)
                # Should have enough travel time in between
                required_next_arr = dep + (next_act.travel_time_mins / 60.0)
                if next_arr < required_next_arr - 0.01: # allow minor float rounding
                    time_overlap_free = False
                    warnings.append(f"Day {day.day_number}: Overlap or insufficient travel time between {act.place.name} and {next_act.place.name}.")

            # 3. Opening hours check
            open_h = act.place.opening_hours["open"]
            close_h = act.place.opening_hours["close"]
            if arr < open_h or dep > close_h:
                opening_hours_ok = False
                warnings.append(f"Day {day.day_number}: {act.place.name} is visited outside opening hours ({act.arrival_time} - {act.departure_time}; open: {decimal_to_time_str(open_h)} - {decimal_to_time_str(close_h)}).")

            # 4. Walking limits check
            if profile.walking_limit == "little" and act.place.walking_level == "active":
                walking_limit_ok = False
                warnings.append(f"Day {day.day_number}: {act.place.name} requires 'active' walking, which exceeds preference 'little'.")

    # Helper function inside validator
    is_valid = budget_ok and time_overlap_free and opening_hours_ok and walking_limit_ok

    return ItineraryValidationReport(
        is_valid=is_valid,
        budget_ok=budget_ok,
        time_overlap_free=time_overlap_free,
        opening_hours_ok=opening_hours_ok,
        walking_limit_ok=walking_limit_ok,
        warnings=warnings
    )

def decimal_to_time_str(decimal_hours: float) -> str:
    hours = int(decimal_hours)
    minutes = int(round((decimal_hours - hours) * 60))
    if minutes == 60:
        hours += 1
        minutes = 0
    return f"{hours:02d}:{minutes:02d}"
