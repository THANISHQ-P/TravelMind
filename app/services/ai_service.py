import re
import json
import urllib.request
import urllib.error
from typing import List
from ..schemas.travel import TravelerProfile
from ..config import settings

INDIA_DESTINATION_ALIASES = {
    "bangalore": "Bengaluru, Karnataka, India",
    "bengaluru": "Bengaluru, Karnataka, India",
    "bangalore, karnataka": "Bengaluru, Karnataka, India",
    "bengaluru, karnataka": "Bengaluru, Karnataka, India",
    "munnar": "Munnar, Kerala, India",
    "munnar, kerala": "Munnar, Kerala, India",
    "vagamon": "Vagamon, Kerala, India",
    "vagamon, kerala": "Vagamon, Kerala, India",
    "ooty": "Ooty, Tamil Nadu, India",
    "ooty, tamil nadu": "Ooty, Tamil Nadu, India",
    "pondicherry": "Pondicherry, Puducherry, India",
    "pondicherry, puducherry": "Pondicherry, Puducherry, India",
    "goa": "Goa, India",
    "jaipur": "Jaipur, Rajasthan, India",
    "jaipur, rajasthan": "Jaipur, Rajasthan, India",
    "manali": "Manali, Himachal Pradesh, India",
    "manali, himachal pradesh": "Manali, Himachal Pradesh, India",
    "wayanad": "Wayanad, Kerala, India",
    "coorg": "Coorg, Karnataka, India",
    "coorg, karnataka": "Coorg, Karnataka, India",
    "mumbai": "Mumbai, Maharashtra, India",
    "delhi": "Delhi, India",
    "chennai": "Chennai, Tamil Nadu, India",
    "kochi": "Kochi, Kerala, India",
    "alleppey": "Alleppey, Kerala, India",
    "alappuzha": "Alappuzha, Kerala, India",
    "kodaikanal": "Kodaikanal, Tamil Nadu, India",
    "varkala": "Varkala, Kerala, India",
    "thekkady": "Thekkady, Kerala, India",
    "mysuru": "Mysuru, Karnataka, India",
    "mysore": "Mysuru, Karnataka, India",
    "hampi": "Hampi, Karnataka, India",
    "hyderabad": "Hyderabad, Telangana, India",
    "udaipur": "Udaipur, Rajasthan, India",
    "jaisalmer": "Jaisalmer, Rajasthan, India",
    "varanasi": "Varanasi, Uttar Pradesh, India",
    "rishikesh": "Rishikesh, Uttarakhand, India",
    "shimla": "Shimla, Himachal Pradesh, India",
    "darjeeling": "Darjeeling, West Bengal, India",
    "gangtok": "Gangtok, Sikkim, India",
    "andaman": "Andaman and Nicobar Islands, India",
    "lakshadweep": "Lakshadweep, India",
    "wayanad, kerala": "Wayanad, Kerala, India",
    "kodaikanal, tamil nadu": "Kodaikanal, Tamil Nadu, India"
}

STATE_NAME_OVERRIDES = {
    "bangalore": "Karnataka",
    "bengaluru": "Karnataka",
    "munnar": "Kerala",
    "vagamon": "Kerala",
    "ooty": "Tamil Nadu",
    "pondicherry": "Puducherry",
    "goa": "Goa",
    "jaipur": "Rajasthan",
    "manali": "Himachal Pradesh",
    "wayanad": "Kerala",
    "coorg": "Karnataka",
    "mumbai": "Maharashtra",
    "delhi": "Delhi",
    "chennai": "Tamil Nadu",
    "kochi": "Kerala",
    "alleppey": "Kerala",
    "alappuzha": "Kerala",
    "kodaikanal": "Tamil Nadu",
    "varkala": "Kerala",
    "thekkady": "Kerala",
    "mysuru": "Karnataka",
    "mysore": "Karnataka",
    "hampi": "Karnataka",
    "hyderabad": "Telangana",
    "udaipur": "Rajasthan",
    "jaisalmer": "Rajasthan",
    "varanasi": "Uttar Pradesh",
    "rishikesh": "Uttarakhand",
    "shimla": "Himachal Pradesh",
    "darjeeling": "West Bengal",
    "gangtok": "Sikkim",
    "andaman": "Andaman and Nicobar Islands",
    "lakshadweep": "Lakshadweep"
}


def get_destination_metadata(raw_destination: str):
    if raw_destination is None:
        return {"destination": "", "state": "", "country": "India"}

    value = canonicalize_destination(raw_destination)
    if not value:
        return {"destination": "", "state": "", "country": "India"}

    normalized = value.strip()
    parts = [p.strip() for p in normalized.split(',') if p.strip()]
    if len(parts) >= 2 and parts[-1].lower() == 'india':
        state = parts[-2] if len(parts) >= 2 else ""
    else:
        state = ""

    key = str(raw_destination or "").strip().lower().replace('  ', ' ')
    discovered_state = STATE_NAME_OVERRIDES.get(key)
    if not discovered_state and key:
        for alias, canonical in INDIA_DESTINATION_ALIASES.items():
            if key == alias or key.startswith(alias + ','):
                state = canonical.split(',')[-2].strip() if len(canonical.split(',')) >= 3 else ""
                discovered_state = state
                break

    return {"destination": value, "state": discovered_state or state or "", "country": "India"}


def canonicalize_destination(raw_destination: str) -> str:
    if raw_destination is None:
        return ""

    value = raw_destination.strip()
    if not value:
        return ""

    lower_value = value.lower().replace("  ", " ")
    if lower_value in {"india", "across india", "travel across india", "in india"}:
        return ""

    for alias, canonical in sorted(INDIA_DESTINATION_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if lower_value == alias or lower_value.startswith(alias + ",") or lower_value.endswith(", " + alias) or alias in lower_value:
            return canonical

    normalized = re.sub(r"[;]+", ",", value)
    normalized = re.sub(r"\s*,\s*", ", ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return ""

    if normalized.lower().endswith("india"):
        return normalized

    return f"{normalized}, India"


def parse_destination_from_text(text: str) -> str:
    if not text:
        return ""

    lower_text = text.lower()
    for alias in sorted(INDIA_DESTINATION_ALIASES.keys(), key=lambda item: len(item), reverse=True):
        if alias in lower_text:
            return INDIA_DESTINATION_ALIASES[alias]

    patterns = [
        r"\bin\s+([a-z][a-z0-9&.,\- ]{1,80}?)(?=\s*(?:for|from|during|with|and|budget|days?|trip|travel|visit|stay|to|$))",
        r"\b(?:travel|visit|visiting|going to|stay in|exploring)\s+([a-z][a-z0-9&.,\- ]{1,80}?)(?=\s*(?:for|from|during|with|and|budget|days?|trip|travel|visit|stay|$))",
        r"\bto\s+([a-z][a-z0-9&.,\- ]{1,80}?)(?=\s*(?:for|from|during|with|and|budget|days?|trip|travel|visit|stay|$))"
    ]

    for pattern in patterns:
        match = re.search(pattern, lower_text)
        if match:
            candidate = match.group(1).strip()
            if candidate and candidate.lower() not in {"india", "across india"}:
                return canonicalize_destination(candidate)

    return ""


def normalize_text(text: str) -> str:
    if not text:
        return ""
    value = text.lower().strip()
    value = re.sub(r"[^a-z0-9\s,₹rupeesk]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def extract_destination(text: str) -> str:
    raw = normalize_text(text)
    if not raw:
        return ""

    aliases = {
        "kochi": "Kochi, Kerala, India",
        "munnar": "Munnar, Kerala, India",
        "goa": "Goa, India",
        "ooty": "Ooty, Tamil Nadu, India",
        "jaipur": "Jaipur, Rajasthan, India",
        "wayanad": "Wayanad, Kerala, India",
        "mysuru": "Mysuru, Karnataka, India",
        "mysore": "Mysuru, Karnataka, India",
        "bengaluru": "Bengaluru, Karnataka, India",
        "bangalore": "Bengaluru, Karnataka, India",
        "chennai": "Chennai, Tamil Nadu, India",
        "pondicherry": "Pondicherry, Puducherry, India",
        "vagamon": "Vagamon, Kerala, India",
        "kodaikanal": "Kodaikanal, Tamil Nadu, India",
        "manali": "Manali, Himachal Pradesh, India",
        "shimla": "Shimla, Himachal Pradesh, India",
        "delhi": "Delhi, India",
        "mumbai": "Mumbai, Maharashtra, India",
        "hyderabad": "Hyderabad, Telangana, India",
        "rishikesh": "Rishikesh, Uttarakhand, India",
        "udaipur": "Udaipur, Rajasthan, India",
        "coorg": "Coorg, Karnataka, India",
    }

    for key, value in aliases.items():
        if re.search(rf"\b{re.escape(key)}\b", raw):
            return value

    for pattern in [
        r"\b(?:in|to|visit|trip to|going to)\s+([a-z][a-z0-9&.,\- ]{1,80}?)(?=\s+(?:for|with|days?|day|budget|rs|rupees|and|$))",
        r"\b(?:stay in|exploring)\s+([a-z][a-z0-9&.,\- ]{1,80}?)(?=\s+(?:for|with|days?|day|budget|rs|rupees|and|$))",
    ]:
        match = re.search(pattern, raw)
        if match:
            candidate = match.group(1).strip()
            if candidate and candidate.lower() not in {"india", "across india"}:
                return canonicalize_destination(candidate)

    return parse_destination_from_text(text)


def extract_duration_days(text: str) -> int:
    raw = normalize_text(text)
    if not raw:
        return 3

    patterns = [
        r"\b(\d+)\s*(?:days?|d)\b",
        r"\bfor\s+(\d+)\s*(?:days?|d)\b",
        r"\b(\d+)\s*day\b",
        r"\b(?:one|two|three|four|five|six|seven)\s*(?:days?|d)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, raw)
        if match:
            value = match.group(1).lower()
            converted = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7}
            if value.isdigit():
                return int(value)
            return converted.get(value, 3)

    return 3


def extract_budget(text: str) -> float:
    raw = normalize_text(text)
    if not raw:
        return 12000.0

    money_matches = re.findall(r"(?:rs|rupees|inr|₹)\s*(\d[\d,]*)(?:\s*k)?", raw)
    if money_matches:
        value = float(money_matches[0].replace(",", ""))
        return value

    k_matches = re.findall(r"(\d+(?:\.\d+)?)\s*k\b", raw)
    if k_matches:
        return float(k_matches[0]) * 1000

    big_numbers = [int(num) for num in re.findall(r"\b\d{4,}\b", raw)]
    if big_numbers:
        return float(max(big_numbers))

    return 12000.0


def extract_categories(text: str) -> List[str]:
    raw = normalize_text(text)
    categories = []
    matcher = {
        "history": ["history", "heritage", "museum", "fort", "palace", "monument"],
        "local food": ["local food", "food", "restaurant", "cafe", "tiffin", "street food", "dining"],
        "nature": ["nature", "beach", "beaches", "sea", "park", "parks", "garden", "gardens", "hills", "waterfall", "lake", "greenery"],
    }

    for label, patterns in matcher.items():
        if any(pattern in raw for pattern in patterns):
            categories.append(label)

    if not categories:
        return ["history", "local food", "nature"]
    return categories


def extract_pace(text: str) -> str:
    raw = normalize_text(text)
    if any(word in raw for word in ["slow", "relaxed", "leisure", "laid back", "easy"]):
        return "slow"
    if any(word in raw for word in ["fast", "packed", "busy", "hectic", "active"]):
        return "fast"
    return "balanced"


def extract_walking_limit(text: str) -> str:
    raw = normalize_text(text)
    if any(word in raw for word in ["lot of walking", "active", "lots of walking", "hiking", "tough"]):
        return "active"
    if any(word in raw for word in ["moderate", "medium walking", "average walking"]):
        return "moderate"
    if any(word in raw for word in ["little walking", "less walking", "very little", "little walking", "little"]):
        return "little"
    return "little"


def parse_preferences_fallback(text: str) -> TravelerProfile:
    destination = extract_destination(text)
    metadata = get_destination_metadata(destination)
    num_days = extract_duration_days(text)
    budget = extract_budget(text)
    categories = extract_categories(text)
    pace = extract_pace(text)
    walking_limit = extract_walking_limit(text)

    return TravelerProfile(
        destination=metadata["destination"],
        state=metadata["state"],
        country=metadata["country"],
        num_days=num_days,
        budget=budget,
        categories=categories,
        pace=pace,
        walking_limit=walking_limit,
        starting_time="09:00",
        locked_places=[]
    )


def parse_preferences_llm(text: str) -> TravelerProfile:
    if not settings.GEMINI_API_KEY:
        return parse_preferences_fallback(text)
    
    # Attempt to query Gemini API (Flash/Pro) for structured json
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    
    prompt = f"""
    You are an AI assistant parsing travel preferences. Parse the following query into JSON matching this Pydantic schema:
    - destination: string (use a single Indian destination name like "Munnar, Kerala, India" or "Bengaluru, Karnataka, India"; if no destination is provided, use an empty string)
    - num_days: integer (between 1 and 7, default 3)
    - budget: float (in Rupees INR, default 12000.0)
    - categories: list of strings (allowed values: "history", "local food", "nature")
    - pace: string ("slow", "balanced", "fast")
    - walking_limit: string ("little", "moderate", "active")

    Important rules:
    - The destination is the primary constraint. Never set destination to "India".
    - If the user mentions "Bangalore" or "Bengaluru", use "Bengaluru, Karnataka, India".
    - If the user mentions "Munnar", use "Munnar, Kerala, India".
    - If the user mentions "Vagamon", use "Vagamon, Kerala, India".
    - If no specific destination is mentioned, use empty string "".

    Query: "{text}"

    Respond ONLY with a valid JSON object matching the schema. No markdown formatting.
    """
    
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=8) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            text_response = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
            data = json.loads(text_response)
            parsed_destination = canonicalize_destination(str(data.get("destination", "")))
            parsed_budget = float(data.get("budget", 12000.0) or 0.0)
            parsed_categories = data.get("categories") or ["history", "local food", "nature"]
            parsed_pace = data.get("pace") or "balanced"
            parsed_walking = data.get("walking_limit") or "little"

            if not parsed_destination or parsed_budget <= 0 or not parsed_categories:
                return parse_preferences_fallback(text)

            return TravelerProfile(
                destination=parsed_destination,
                num_days=int(data.get("num_days", 3)),
                budget=parsed_budget,
                categories=parsed_categories,
                pace=parsed_pace,
                walking_limit=parsed_walking,
                starting_time="09:00",
                locked_places=[]
            )
    except Exception:
        # Fall back to regex parser on failure
        return parse_preferences_fallback(text)
