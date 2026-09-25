"""
Room Listings Seeder
====================
Generates realistic room listings for the RoomMate Finder demo database.

The listings are derived from the survey data already loaded into
`user_preferences`, so that survey respondents actually get matches when the
Room Matching Agent runs:

  * Location  - room locations embed the five survey area categories
                ("Near University/College Area", "Residential Area", ...)
                so the agent's `location ILIKE %preferred_location%` filter hits.
  * Price     - rents are drawn inside the budget bands the survey produced
                (3k-8k, 8k-20k, 20k-40k, 40k-80k PKR), weighted by how many
                respondents fall in each band.
  * Room type - Single / Shared / Master mixed in line with the survey's
                preferred_room_type split (Shared is the clear majority).
  * Rules     - most rooms are non-smoking and pet-free, because the agent
                hard-filters those out for respondents who said they are not
                comfortable with smoking / pets (the majority).

Owners are existing users from the same area category, so the "Contact Owner"
flow shows a plausible owner. Owners missing a phone number get one generated
(the survey export did not include phone numbers).

Usage:
    python add_rooms_for_matching.py                # add ~180 rooms
    python add_rooms_for_matching.py --reset        # wipe rooms first
    python add_rooms_for_matching.py --count 250    # choose how many
"""

import argparse
import logging
import os
import random
import sys
from datetime import datetime, timedelta

# Run from the project root regardless of where the script is invoked from.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

logging.getLogger('sqlalchemy').setLevel(logging.ERROR)
logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)

from dotenv import load_dotenv

load_dotenv()

from backend.app import create_app                      # noqa: E402
from backend.database import db                         # noqa: E402
from backend.models.room import Room                    # noqa: E402
from backend.models.user import User                    # noqa: E402


# ---------------------------------------------------------------------------
# Survey-derived reference data
# ---------------------------------------------------------------------------

# The five area categories the survey offered, mapped to real localities around
# The Islamia University of Bahawalpur (respondents are IUB students).
# A room's `location` is "<locality>, <category>" so that the category is still
# a substring - that is what the Room Matching Agent filters on.
AREAS = {
    'Near University/College Area': [
        'Baghdad-ul-Jadeed', 'Abbasia Campus Road', 'Khawaja Farid Colony',
        'University Chowk', 'Medical Colony',
    ],
    'Residential Area': [
        'Model Town A', 'Model Town B', 'Satellite Town',
        'Gulshan-e-Farid', 'Shadab Colony',
    ],
    'Downtown/City Center': [
        'Farid Gate', 'Noor Mahal Road', 'Circular Road',
        'Shahi Bazaar', 'Machhli Bazaar',
    ],
    'Near Workplace/Office District': [
        'Bahawalpur Cantt', 'Commercial Area Model Town',
        'Dring Stadium Road', 'Cantt Bazaar',
    ],
    'Suburban Area': [
        'Yazman Road', 'Ahmadpur Road', 'Hasilpur Road', 'Bahawalpur Bypass',
    ],
}

# How many rooms each area gets, roughly proportional to survey demand
# (205 / 45 / 29 / 23 / 17 respondents).
AREA_WEIGHTS = {
    'Near University/College Area': 0.56,
    'Residential Area': 0.16,
    'Downtown/City Center': 0.12,
    'Near Workplace/Office District': 0.09,
    'Suburban Area': 0.07,
}

# Budget bands present in user_preferences, with the share of rooms to price
# into each one. Weighted towards the 8k-20k band, where most respondents sit.
BUDGET_BANDS = [
    ((3000, 8000), 0.20),
    ((8000, 20000), 0.55),
    ((20000, 40000), 0.18),
    ((40000, 80000), 0.07),
]

# Survey preferred_room_type split was Shared 187 / Single 112 / Any 20.
ROOM_TYPE_WEIGHTS = [('Shared', 0.50), ('Single', 0.35), ('Master', 0.15)]

# Amenities the scoring function rewards come first and appear most often.
CORE_AMENITIES = ['WiFi', 'AC', 'Kitchen access', 'Parking']
EXTRA_AMENITIES = [
    'Furnished', 'Attached Bathroom', 'Study Desk', 'Laundry', 'Backup Generator',
    'Water Filter', 'Balcony', 'Rooftop Access', 'Security Guard',
    'Separate Entrance', 'Gas Connection', 'Weekly Cleaning',
]

# Room artwork shipped with the frontend (frontend/images/rooms/*.svg). These
# are local on purpose: remote photo URLs leave broken tiles whenever the
# machine running the demo is offline, and they are relative to the page so they
# work wherever the frontend is hosted.
ROOM_IMAGES = [f'images/rooms/room-{i:02d}.svg' for i in range(1, 11)]

TITLE_PATTERNS = [
    '{adjective} {type} in {locality}',
    '{type} with {highlight} - {locality}',
    '{adjective} {type} near {landmark}',
    '{type} for {audience} in {locality}',
]

ADJECTIVES = [
    'Bright', 'Spacious', 'Furnished', 'Newly Renovated', 'Quiet',
    'Affordable', 'Well-Lit', 'Modern', 'Cosy', 'Airy',
]

TYPE_LABELS = {
    'Single': 'Single Room',
    'Shared': 'Shared Room',
    'Master': 'Master Bedroom',
}

HIGHLIGHTS = [
    'Attached Bath', 'Study Corner', 'Private Balcony', 'Backup Power',
    'Separate Entrance', 'Rooftop Access',
]

# Landmarks are per area, so a title never advertises a campus that is on the
# other side of the city from the room.
LANDMARKS = {
    'Near University/College Area': [
        'IUB Baghdad Campus', 'Abbasia Campus', 'Bahawal Victoria Hospital',
        'University Chowk',
    ],
    'Residential Area': [
        'Model Town Market', 'Satellite Town Park', 'Gulshan-e-Farid Masjid',
    ],
    'Downtown/City Center': [
        'Noor Mahal', 'Fawara Chowk', 'Farid Gate', 'Shahi Bazaar',
    ],
    'Near Workplace/Office District': [
        'Dring Stadium', 'Cantt Bazaar', 'Model Town Commercial Area',
    ],
    'Suburban Area': [
        'Bahawalpur Bypass', 'Yazman Road Stop', 'Ahmadpur Interchange',
    ],
}

AUDIENCES = ['Students', 'Working Professionals', 'Postgrad Students', 'Job Holders']

DESCRIPTION_OPENERS = [
    'Well-ventilated room on a calm street, a short walk from daily-use shops.',
    'Clean, freshly painted room in a family-maintained house.',
    'Comfortable room in a secure building with a caretaker on site.',
    'Peaceful room suited to students who need quiet study hours.',
    'Bright room with large windows and good natural light through the day.',
    'Recently renovated room with new fittings and fresh paint.',
    'Roomy accommodation with dedicated storage and a study area.',
    'Tidy room in a well-kept portion with a separate entrance.',
]

DESCRIPTION_CLOSERS = [
    'Rickshaw and bus stops are a couple of minutes away.',
    'Grocery stores, a pharmacy and eateries are within walking distance.',
    'Reliable water supply and a backup arrangement for load-shedding.',
    'Landlord lives nearby and responds quickly to maintenance requests.',
    'Ideal for anyone who wants a short, predictable commute.',
    'Quiet neighbours and a respectful, family-friendly environment.',
]


def weighted_choice(pairs):
    """Pick a value from [(value, weight), ...]."""
    values, weights = zip(*pairs)
    return random.choices(values, weights=weights, k=1)[0]


def make_phone():
    """Generate a plausible Pakistani mobile number."""
    network = random.choice(['300', '301', '311', '321', '331', '333', '345'])
    return f"+92 {network}-{random.randint(1000000, 9999999)}"


def build_title(room_type, locality, category):
    pattern = random.choice(TITLE_PATTERNS)
    return pattern.format(
        adjective=random.choice(ADJECTIVES),
        type=TYPE_LABELS[room_type],
        locality=locality,
        highlight=random.choice(HIGHLIGHTS),
        landmark=random.choice(LANDMARKS[category]),
        audience=random.choice(AUDIENCES),
    )


def build_description(room_type, locality, category, amenities, rent):
    parts = [
        random.choice(DESCRIPTION_OPENERS),
        f"{TYPE_LABELS[room_type]} in {locality} ({category.lower()}).",
    ]
    if amenities:
        parts.append(f"Includes {', '.join(amenities[:4])}.")
    parts.append(f"Rent is PKR {rent:,} per month, utilities billed separately.")
    parts.append(random.choice(DESCRIPTION_CLOSERS))
    return ' '.join(parts)


def pick_amenities(room_type, rent):
    """Higher-rent rooms list more amenities; core ones are common everywhere."""
    amenities = [a for a in CORE_AMENITIES if random.random() < 0.72]
    if not amenities:
        amenities = [random.choice(CORE_AMENITIES)]

    if rent >= 35000:
        extra_count = random.randint(3, 5)
    elif rent >= 18000:
        extra_count = random.randint(2, 4)
    else:
        extra_count = random.randint(1, 3)

    amenities += random.sample(EXTRA_AMENITIES, k=extra_count)

    if room_type == 'Master' and 'Attached Bathroom' not in amenities:
        amenities.append('Attached Bathroom')

    # Preserve order, drop duplicates.
    return list(dict.fromkeys(amenities))


def build_room(owner, category, localities, band=None,
               smoking_allowed=None, pets_allowed=None):
    """Create one Room for the given owner inside the given area category.

    `band`, `smoking_allowed` and `pets_allowed` can be pinned so the coverage
    pass can build a room that satisfies a specific survey profile.
    """
    locality = random.choice(localities)
    band_min, band_max = band if band else weighted_choice(BUDGET_BANDS)

    # Keep the rent comfortably inside the band so it survives the agent's
    # `budget_min <= rent <= budget_max` filter for users in that band.
    low = int(band_min * 1.05)
    high = int(band_max * 0.95)
    rent = random.randrange(low, high + 1, 500)

    room_type = weighted_choice(ROOM_TYPE_WEIGHTS)
    amenities = pick_amenities(room_type, rent)

    if room_type == 'Master':
        bedrooms, bathrooms = 1, 1.0
    elif room_type == 'Single':
        bedrooms, bathrooms = 1, random.choice([1.0, 0.5])
    else:
        bedrooms, bathrooms = random.choice([1, 2]), 0.5

    return Room(
        owner_id=owner.user_id,
        title=build_title(room_type, locality, category),
        description=build_description(room_type, locality, category, amenities, rent),
        location=f"{locality}, {category}",
        rent_price=rent,
        room_type=room_type,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        amenities=amenities,
        # Most respondents are not comfortable with smoking or pets, and the
        # agent hard-filters those rooms out for them, so keep both mostly off.
        smoking_allowed=(random.random() < 0.18) if smoking_allowed is None
        else smoking_allowed,
        pets_allowed=(random.random() < 0.35) if pets_allowed is None
        else pets_allowed,
        images=random.sample(ROOM_IMAGES, k=random.randint(1, 3)),
        is_available=True,
        available_from=datetime.utcnow().date() + timedelta(days=random.randint(0, 45)),
        lease_duration_months=weighted_choice([(6, 0.7), (12, 0.25), (24, 0.05)]),
    )


def matches_profile(room, budget_min, budget_max, location, smoking_ok, pets_ok):
    """Mirror the hard filters the Room Matching Agent applies."""
    rent = float(room.rent_price)
    if not budget_min <= rent <= budget_max:
        return False
    if location and location.strip().lower() not in room.location.lower():
        return False
    if not smoking_ok and room.smoking_allowed:
        return False
    if not pets_ok and room.pets_allowed:
        return False
    return True


def band_for_budget(budget_min, budget_max):
    """Pick the budget band that sits inside a respondent's range."""
    candidates = [b for (b, _) in BUDGET_BANDS
                  if b[0] >= budget_min and b[1] <= budget_max]
    if candidates:
        return random.choice(candidates)
    # Wide or unusual range: price into the middle of the range itself.
    return (budget_min, budget_max)


def ensure_profile_coverage(session, rooms, owners_by_area, all_users, min_matches):
    """Top up listings so every survey profile has at least `min_matches` rooms.

    Without this, a respondent with an uncommon combination (say a high budget
    in the office district who is not comfortable with pets) can open the app
    and see nothing at all.
    """
    from backend.models.preference import UserPreference

    profiles = session.query(
        UserPreference.budget_min, UserPreference.budget_max,
        UserPreference.preferred_location, UserPreference.smoking_ok,
        UserPreference.pets_ok,
    ).distinct().all()

    added = []
    for budget_min, budget_max, location, smoking_ok, pets_ok in profiles:
        budget_min = float(budget_min or 0)
        budget_max = float(budget_max or 0)
        pool = rooms + added
        found = sum(1 for room in pool
                    if matches_profile(room, budget_min, budget_max,
                                       location, smoking_ok, pets_ok))
        if found >= min_matches:
            continue

        category = location if location in AREAS else random.choice(list(AREAS))
        localities = AREAS[category]
        owners = owners_by_area.get(category) or all_users

        for _ in range(min_matches - found):
            room = build_room(
                random.choice(owners), category, localities,
                band=band_for_budget(budget_min, budget_max),
                # Rooms that allow neither are visible to every respondent.
                smoking_allowed=False,
                pets_allowed=False,
            )
            is_valid, errors = room.validate()
            if not is_valid:
                print(f"    [!] Skipping invalid coverage room: {errors}")
                continue
            session.add(room)
            added.append(room)

    return added


def main():
    parser = argparse.ArgumentParser(description='Seed room listings for the demo database')
    parser.add_argument('--reset', action='store_true', help='Delete existing rooms first')
    parser.add_argument('--count', type=int, default=180,
                        help='Total rooms to create (default: 180)')
    parser.add_argument('--seed', type=int, default=None,
                        help='Random seed for reproducible data')
    parser.add_argument('--min-matches', type=int, default=5,
                        help='Minimum rooms guaranteed per survey profile (default: 5)')
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    app = create_app()

    with app.app_context():
        print('=' * 70)
        print('Room Listings Seeder')
        print('=' * 70)
        print(f"Database: {app.config.get('SQLALCHEMY_DATABASE_URI')}")

        if args.reset:
            deleted = db.session.query(Room).delete()
            db.session.commit()
            print(f"\n[*] Cleared {deleted} existing room(s)")

        users = db.session.query(User).filter(User.is_active.is_(True)).all()
        if not users:
            print('\n[!] No active users found - load the survey data first.')
            return

        # Group candidate owners by the area they live in, so a room is listed
        # by somebody who plausibly lives there.
        owners_by_area = {area: [] for area in AREAS}
        for user in users:
            if user.city in owners_by_area:
                owners_by_area[user.city].append(user)
        # Areas with no resident fall back to the whole user pool.
        for area, pool in owners_by_area.items():
            if not pool:
                owners_by_area[area] = users

        print(f"\n[*] {len(users)} active users available as owners")
        print(f"[*] Generating {args.count} room(s)...")

        rooms = []
        for area, weight in AREA_WEIGHTS.items():
            area_count = max(1, round(args.count * weight))
            localities = AREAS[area]
            pool = owners_by_area[area]
            for _ in range(area_count):
                owner = random.choice(pool)
                room = build_room(owner, area, localities)
                is_valid, errors = room.validate()
                if not is_valid:
                    print(f"    [!] Skipping invalid room: {errors}")
                    continue
                rooms.append(room)
                db.session.add(room)

        extra = ensure_profile_coverage(
            db.session, rooms, owners_by_area, users, args.min_matches
        )
        if extra:
            print(f"[*] Added {len(extra)} room(s) to cover under-served survey profiles")
            rooms += extra

        # Owners need a contact number for the "Contact Owner" modal.
        owner_ids = {room.owner_id for room in rooms}
        filled_phones = 0
        for user in users:
            if user.user_id in owner_ids and not user.phone:
                user.phone = make_phone()
                filled_phones += 1

        db.session.commit()

        total = db.session.query(Room).count()
        print(f"\n[OK] Created {len(rooms)} room(s); {total} total in database")
        print(f"[OK] Generated phone numbers for {filled_phones} owner(s)")

        print('\n[*] Rooms by area:')
        area_totals = {}
        for location, count in db.session.query(
            Room.location, db.func.count(Room.room_id)
        ).group_by(Room.location).all():
            category = location.split(', ', 1)[-1]
            area_totals[category] = area_totals.get(category, 0) + count
        for category, count in sorted(area_totals.items(), key=lambda kv: -kv[1]):
            print(f"    {category:34s} {count}")

        print('\n[*] Rooms by budget band:')
        for (band_min, band_max), _ in BUDGET_BANDS:
            count = db.session.query(Room).filter(
                Room.rent_price >= band_min, Room.rent_price <= band_max
            ).count()
            print(f"    PKR {band_min:>6,} - {band_max:<6,}  {count}")

        print('\n[*] Rooms by type:')
        for room_type, count in db.session.query(
            Room.room_type, db.func.count(Room.room_id)
        ).group_by(Room.room_type).all():
            print(f"    {room_type:10s} {count}")

        print('\n[*] Room matching is ready. Restart the backend to pick up the new data.')
        print('=' * 70)


if __name__ == '__main__':
    main()
