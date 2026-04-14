"""
Hostel Search Service
=====================
Uses Google Places API to find real hostels / student accommodation
for a given city, then stores them as Room records in the database.

Triggered automatically on user registration when a new city is seen.
Can also be called manually via POST /rooms/import-hostels.
"""

import os
import requests
import logging
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

# Reuse the same Google API key already used for Gemini
_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# System account that "owns" auto-imported hostel listings
SYSTEM_USER_EMAIL = "system@roommate-ai.internal"

# How many Places results to import per city (max 20 from one page)
MAX_HOSTELS_PER_CITY = 15

# Minimum existing rooms before we skip fetching for a city
EXISTING_ROOMS_THRESHOLD = 5


def _get_or_create_system_user():
    """Return (or lazily create) the system owner account."""
    from backend.database import db
    from backend.models import User

    user = User.query.filter_by(email=SYSTEM_USER_EMAIL).first()
    if user:
        return user

    user = User(
        email=SYSTEM_USER_EMAIL,
        full_name="RoomMate AI",
        city="System",
        is_active=True,
    )
    # Random secure password — this account is never logged into
    user.set_password(os.urandom(24).hex())
    db.session.add(user)
    db.session.commit()
    logger.info("Created system user for hostel imports.")
    return user


def _fetch_places(city: str) -> list[dict]:
    """
    Call Google Places Text Search API and return raw result dicts.
    Falls back gracefully if the API key is missing or the call fails.
    """
    if not _API_KEY:
        logger.warning("GOOGLE_API_KEY not set — skipping hostel fetch.")
        return []

    query = f"hostel student accommodation paying guest in {city} Pakistan"
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": query,
        "key": _API_KEY,
        "language": "en",
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        status = data.get("status", "UNKNOWN")

        if status == "OK":
            return data.get("results", [])

        if status in ("ZERO_RESULTS", "NOT_FOUND"):
            logger.info("No Places results for city '%s'.", city)
        else:
            logger.warning("Places API status '%s' for city '%s'.", status, city)

    except Exception as exc:
        logger.error("Places API request failed: %s", exc)

    return []


def _place_to_room(place: dict, city: str, owner_id: int):
    """Convert a Google Places result dict into a Room model instance."""
    from backend.models import Room

    name = place.get("name", "Hostel")
    address = place.get("formatted_address", city)
    rating = place.get("rating")
    price_level = place.get("price_level", 1)  # 0-4 scale

    # Estimate rent from price_level (PKR/month)
    price_map = {0: 3000, 1: 6000, 2: 12000, 3: 22000, 4: 40000}
    rent = price_map.get(price_level, 6000)

    rating_str = f"  ⭐ {rating}/5" if rating else ""
    description = (
        f"Real hostel/accommodation in {city} — sourced from Google Maps.{rating_str}\n"
        f"Address: {address}\n"
        f"Contact the hostel directly for availability and exact pricing."
    )

    amenities = ["WiFi"]
    types = place.get("types", [])
    if "lodging" in types:
        amenities.append("Furnished")
    if "meal_delivery" in types or "restaurant" in types:
        amenities.append("Meals included")

    # Use Google Maps URL as a stand-in image (placeholder)
    place_id = place.get("place_id", "")
    photos = place.get("photos", [])
    images = []
    if photos and _API_KEY:
        ref = photos[0].get("photo_reference", "")
        if ref:
            images.append(
                f"https://maps.googleapis.com/maps/api/place/photo"
                f"?maxwidth=800&photoreference={ref}&key={_API_KEY}"
            )

    room = Room(
        owner_id=owner_id,
        title=name,
        description=description,
        location=city,
        rent_price=rent,
        room_type="Shared",
        bedrooms=1,
        bathrooms=1,
        amenities=amenities,
        images=images,
        smoking_allowed=False,
        pets_allowed=False,
        is_available=True,
        lease_duration_months=6,
    )
    return room


def fetch_and_save_hostels(city: str) -> int:
    """
    Main entry point.  Fetch real hostels for *city* from Google Places and
    persist them as Room records.

    Returns the number of newly saved rooms (0 if city already has enough
    listings or if the API call fails).
    """
    from backend.database import db
    from backend.models import Room

    if not city or not city.strip():
        return 0

    city = city.strip()

    # Skip if we already have enough rooms for this city
    existing = Room.query.filter(
        Room.location.ilike(f"%{city}%"),
        Room.is_available == True,  # noqa: E712
    ).count()

    if existing >= EXISTING_ROOMS_THRESHOLD:
        logger.info(
            "City '%s' already has %d rooms — skipping Places fetch.", city, existing
        )
        return 0

    places = _fetch_places(city)
    if not places:
        return 0

    system_user = _get_or_create_system_user()
    saved = 0

    for place in places[:MAX_HOSTELS_PER_CITY]:
        name = place.get("name", "")
        # Skip duplicates
        already = Room.query.filter_by(title=name, location=city).first()
        if already:
            continue

        room = _place_to_room(place, city, system_user.user_id)
        db.session.add(room)
        saved += 1

    if saved:
        try:
            db.session.commit()
            logger.info("Saved %d hostel listings for '%s'.", saved, city)
        except Exception as exc:
            db.session.rollback()
            logger.error("Failed to save hostels for '%s': %s", city, exc)
            saved = 0

    return saved
