"""
Seed Rooms Data
===============
Creates realistic Pakistani hostel / room listings for major cities.
No Google API key required — all data is hardcoded.

Usage (from roommate-matching-system/):
    python seed_rooms.py                     # uses local SQLite / .env DATABASE_URL
    DATABASE_URL="postgresql://..." python seed_rooms.py   # production Neon DB

Options:
    --clear   Delete all existing rooms before seeding
    --city    Seed only one city, e.g. --city Bahawalpur
"""

import sys
import os
import argparse

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv()

parser = argparse.ArgumentParser()
parser.add_argument("--clear", action="store_true", help="Delete all existing rooms first")
parser.add_argument("--city", type=str, default=None, help="Seed only this city")
args = parser.parse_args()

# ---------------------------------------------------------------------------
# Room data — realistic Pakistani listings across university cities
# ---------------------------------------------------------------------------
ROOMS = [
    # ── Bahawalpur (IUB) ──────────────────────────────────────────────────
    {
        "city": "Bahawalpur",
        "title": "Male Hostel Near IUB Gate 1",
        "description": "Clean male hostel 5 minutes walk from Islamia University Bahawalpur Gate 1. Shared rooms available. Meals optional. Generator backup. PTCL WiFi included.",
        "location": "Bahawalpur",
        "rent_price": 5500,
        "room_type": "Shared",
        "bedrooms": 1,
        "bathrooms": 1,
        "amenities": ["WiFi", "Generator Backup", "Water Cooler", "Study Room"],
        "smoking_allowed": False,
        "pets_allowed": False,
        "lease_duration_months": 6,
        "owner_name": "Haji Iqbal", "owner_email": "iqbal.hostel.bwp@rooms.pk", "owner_phone": "0300-6581234",
    },
    {
        "city": "Bahawalpur",
        "title": "Female Hostel IUB Area — Safe & Furnished",
        "description": "Fully furnished female hostel near IUB. 24/7 security guard, CCTV, warden on premises. Separate bathroom per room. Meals available at extra cost.",
        "location": "Bahawalpur",
        "rent_price": 7000,
        "room_type": "Single",
        "bedrooms": 1,
        "bathrooms": 1,
        "amenities": ["Furnished", "WiFi", "24/7 Security", "CCTV", "AC"],
        "smoking_allowed": False,
        "pets_allowed": False,
        "lease_duration_months": 6,
        "owner_name": "Mrs. Sadia", "owner_email": "sadia.hostel.bwp@rooms.pk", "owner_phone": "0301-7892345",
    },
    {
        "city": "Bahawalpur",
        "title": "Affordable Shared Room — University Road BWP",
        "description": "Budget-friendly 3-bed shared room on University Road. Ideal for first-year students. Common kitchen, prayer area, and study lounge. Monthly rent includes electricity up to Rs 1000.",
        "location": "Bahawalpur",
        "rent_price": 4000,
        "room_type": "Shared",
        "bedrooms": 1,
        "bathrooms": 1,
        "amenities": ["WiFi", "Kitchen Access", "Prayer Area"],
        "smoking_allowed": False,
        "pets_allowed": False,
        "lease_duration_months": 12,
        "owner_name": "M. Akram", "owner_email": "akram.rooms.bwp@rooms.pk", "owner_phone": "0302-1234567",
    },
    {
        "city": "Bahawalpur",
        "title": "Single AC Room — Model Town BWP",
        "description": "Private single room with attached bath in a quiet residential area. AC, inverter backup, fast Fiber internet. Walking distance from main bazaar and IUB engineering campus.",
        "location": "Bahawalpur",
        "rent_price": 12000,
        "room_type": "Single",
        "bedrooms": 1,
        "bathrooms": 1,
        "amenities": ["AC", "Attached Bath", "WiFi", "Inverter Backup", "Furnished"],
        "smoking_allowed": False,
        "pets_allowed": False,
        "lease_duration_months": 3,
        "owner_name": "Zafar Hussain", "owner_email": "zafar.rooms.bwp@rooms.pk", "owner_phone": "0345-9876543",
    },
    {
        "city": "Bahawalpur",
        "title": "Master Room With Private Bath — Satellite Town BWP",
        "description": "Spacious master bedroom with private bathroom in a well-maintained house. Satellite Town, close to Shopping Mall and IUB. Shared kitchen, lounge, and rooftop. Families in house — very safe.",
        "location": "Bahawalpur",
        "rent_price": 18000,
        "room_type": "Master",
        "bedrooms": 1,
        "bathrooms": 1,
        "amenities": ["Attached Bath", "AC", "WiFi", "Furnished", "Rooftop", "Kitchen Access"],
        "smoking_allowed": False,
        "pets_allowed": False,
        "lease_duration_months": 6,
        "owner_name": "Rashid Family", "owner_email": "rashid.rooms.bwp@rooms.pk", "owner_phone": "0300-4561234",
    },

    # ── Islamabad ─────────────────────────────────────────────────────────
    {
        "city": "Islamabad",
        "title": "Student Hostel — G-9 Islamabad",
        "description": "Well-known student hostel in G-9. Shared rooms. COMSATS and NUST students preferred. WiFi, laundry, canteen, study hall. Monthly charges include utilities.",
        "location": "Islamabad",
        "rent_price": 9000,
        "room_type": "Shared",
        "bedrooms": 1,
        "bathrooms": 1,
        "amenities": ["WiFi", "Laundry", "Canteen", "Study Hall", "Generator Backup"],
        "smoking_allowed": False,
        "pets_allowed": False,
        "lease_duration_months": 6,
        "owner_name": "Capital Hostels", "owner_email": "capital.hostel.isb@rooms.pk", "owner_phone": "051-2345678",
    },
    {
        "city": "Islamabad",
        "title": "Single Room in F-7 — Prime Location",
        "description": "Clean single room in a shared apartment in F-7/3. Great location — Jinnah Super, Super Market nearby. 3 flatmates (professionals), shared kitchen and lounge. No smokers.",
        "location": "Islamabad",
        "rent_price": 22000,
        "room_type": "Single",
        "bedrooms": 1,
        "bathrooms": 1,
        "amenities": ["WiFi", "Furnished", "Kitchen Access", "Washing Machine"],
        "smoking_allowed": False,
        "pets_allowed": False,
        "lease_duration_months": 6,
        "owner_name": "Ahmed Raza", "owner_email": "ahmed.rooms.isb@rooms.pk", "owner_phone": "0312-3456789",
    },
    {
        "city": "Islamabad",
        "title": "Shared Flat — I-8 Islamabad (Female Only)",
        "description": "Female-only shared apartment in I-8 Markaz. 2 rooms available. Fully furnished, 24/7 electricity via solar + WAPDA. Close to Polyclinic, PIMS hospital.",
        "location": "Islamabad",
        "rent_price": 18000,
        "room_type": "Shared",
        "bedrooms": 1,
        "bathrooms": 1,
        "amenities": ["Furnished", "WiFi", "Solar Electricity", "Washing Machine", "AC"],
        "smoking_allowed": False,
        "pets_allowed": False,
        "lease_duration_months": 6,
        "owner_name": "Sara Khan", "owner_email": "sara.rooms.isb@rooms.pk", "owner_phone": "0321-9876543",
    },
    {
        "city": "Islamabad",
        "title": "Master Bedroom — E-11 Islamabad",
        "description": "Spacious master room with attached bath in a 3-bedroom flat. E-11/2, near NUST H-12. Two professional male flatmates. Balcony, parking available. PTCL fiber internet.",
        "location": "Islamabad",
        "rent_price": 35000,
        "room_type": "Master",
        "bedrooms": 1,
        "bathrooms": 1,
        "amenities": ["Attached Bath", "WiFi", "Furnished", "Parking", "Balcony", "AC"],
        "smoking_allowed": False,
        "pets_allowed": False,
        "lease_duration_months": 12,
        "owner_name": "Usman Malik", "owner_email": "usman.rooms.isb@rooms.pk", "owner_phone": "0333-1234567",
    },

    # ── Lahore ────────────────────────────────────────────────────────────
    {
        "city": "Lahore",
        "title": "Hostel Near LUMS — DHA Phase 5",
        "description": "Student-friendly hostel 10 minutes from LUMS and UET. Clean rooms, housekeeping twice a week, laundry facility, fast internet. Meals available.",
        "location": "Lahore",
        "rent_price": 11000,
        "room_type": "Shared",
        "bedrooms": 1,
        "bathrooms": 1,
        "amenities": ["WiFi", "Laundry", "Housekeeping", "Meals Available", "AC"],
        "smoking_allowed": False,
        "pets_allowed": False,
        "lease_duration_months": 6,
        "owner_name": "DHA Hostels", "owner_email": "dha.hostel.lhr@rooms.pk", "owner_phone": "042-3456789",
    },
    {
        "city": "Lahore",
        "title": "Single Room — Johar Town Near UET",
        "description": "Neat single room in Johar Town, 5 min drive from UET Lahore. In a family house. Shared kitchen, TV lounge. Electricity 24/7 (UPS + solar). Safe neighbourhood.",
        "location": "Lahore",
        "rent_price": 14000,
        "room_type": "Single",
        "bedrooms": 1,
        "bathrooms": 1,
        "amenities": ["WiFi", "Solar Electricity", "Kitchen Access", "UPS Backup"],
        "smoking_allowed": False,
        "pets_allowed": False,
        "lease_duration_months": 6,
        "owner_name": "Tariq Ahmad", "owner_email": "tariq.rooms.lhr@rooms.pk", "owner_phone": "0300-4567891",
    },
    {
        "city": "Lahore",
        "title": "Luxury Master Room — Gulberg III",
        "description": "Premium master bedroom with en-suite bath in a luxury apartment. Gulberg III, walking distance from MM Alam Road. Includes parking, gym access, security guard.",
        "location": "Lahore",
        "rent_price": 45000,
        "room_type": "Master",
        "bedrooms": 1,
        "bathrooms": 1,
        "amenities": ["Attached Bath", "Furnished", "WiFi", "Gym Access", "Parking", "AC", "24/7 Security"],
        "smoking_allowed": False,
        "pets_allowed": False,
        "lease_duration_months": 12,
        "owner_name": "Premium Living LHR", "owner_email": "premium.rooms.lhr@rooms.pk", "owner_phone": "0321-4567890",
    },
    {
        "city": "Lahore",
        "title": "Female Hostel — Model Town Lahore",
        "description": "Secure female hostel in Model Town Extension. Warden present. Study hall, common kitchen, prayer room. Biometric gate access. Only female students/professionals.",
        "location": "Lahore",
        "rent_price": 8500,
        "room_type": "Shared",
        "bedrooms": 1,
        "bathrooms": 1,
        "amenities": ["WiFi", "Study Hall", "Prayer Room", "Biometric Access", "Kitchen Access"],
        "smoking_allowed": False,
        "pets_allowed": False,
        "lease_duration_months": 6,
        "owner_name": "Model Town Hostel", "owner_email": "mt.hostel.lhr@rooms.pk", "owner_phone": "042-5555678",
    },

    # ── Karachi ───────────────────────────────────────────────────────────
    {
        "city": "Karachi",
        "title": "Hostel Near FAST-NUCES — Block 13D",
        "description": "Student hostel in Block 13-D, Gulshan-e-Iqbal. Close to FAST-NUCES, NEDUET. Air-cooled rooms, generator backup, WiFi, 24-hr security.",
        "location": "Karachi",
        "rent_price": 8000,
        "room_type": "Shared",
        "bedrooms": 1,
        "bathrooms": 1,
        "amenities": ["WiFi", "Generator Backup", "Air Cooler", "24/7 Security"],
        "smoking_allowed": False,
        "pets_allowed": False,
        "lease_duration_months": 6,
        "owner_name": "Gulshan Hostel KHI", "owner_email": "gulshan.hostel.khi@rooms.pk", "owner_phone": "021-3456789",
    },
    {
        "city": "Karachi",
        "title": "Single Room — Defence Phase 6 Karachi",
        "description": "Modern single room in a 4-bedroom flat in DHA Phase 6. 3 professional flatmates. Fully furnished, fast internet, generator. Near Sea View.",
        "location": "Karachi",
        "rent_price": 28000,
        "room_type": "Single",
        "bedrooms": 1,
        "bathrooms": 1,
        "amenities": ["Furnished", "WiFi", "Generator Backup", "AC", "Washing Machine", "Parking"],
        "smoking_allowed": False,
        "pets_allowed": False,
        "lease_duration_months": 6,
        "owner_name": "Ali Shahid", "owner_email": "ali.rooms.khi@rooms.pk", "owner_phone": "0312-5678901",
    },

    # ── Rawalpindi ────────────────────────────────────────────────────────
    {
        "city": "Rawalpindi",
        "title": "Hostel Near PIMS / AFMC — Chaklala",
        "description": "Affordable hostel near PIMS and AFMC Rawalpindi. Medical students preferred. Study rooms, 24/7 hot water, generator backup, meals available.",
        "location": "Rawalpindi",
        "rent_price": 7500,
        "room_type": "Shared",
        "bedrooms": 1,
        "bathrooms": 1,
        "amenities": ["WiFi", "Study Room", "Hot Water", "Meals Available", "Generator Backup"],
        "smoking_allowed": False,
        "pets_allowed": False,
        "lease_duration_months": 12,
        "owner_name": "Chaklala Hostel RWP", "owner_email": "chaklala.hostel.rwp@rooms.pk", "owner_phone": "051-4567890",
    },
    {
        "city": "Rawalpindi",
        "title": "Single Room — Bahria Town Phase 4",
        "description": "Well-maintained single room in Bahria Town Phase 4. In a family-owned house. Solar + WAPDA, Fiber internet, attached bath.",
        "location": "Rawalpindi",
        "rent_price": 19000,
        "room_type": "Single",
        "bedrooms": 1,
        "bathrooms": 1,
        "amenities": ["Attached Bath", "WiFi", "Solar Electricity", "Furnished"],
        "smoking_allowed": False,
        "pets_allowed": False,
        "lease_duration_months": 6,
        "owner_name": "Bashir Ahmed", "owner_email": "bashir.rooms.rwp@rooms.pk", "owner_phone": "0300-8765432",
    },

    # ── Multan ────────────────────────────────────────────────────────────
    {
        "city": "Multan",
        "title": "Male Hostel Near BUITEMS / BZU — Multan",
        "description": "Decent male hostel near Bahauddin Zakariya University (BZU). Shared rooms for 2-3. Daily cleaning, WiFi, CCTV, emergency generator.",
        "location": "Multan",
        "rent_price": 5000,
        "room_type": "Shared",
        "bedrooms": 1,
        "bathrooms": 1,
        "amenities": ["WiFi", "CCTV", "Generator Backup", "Daily Cleaning"],
        "smoking_allowed": False,
        "pets_allowed": False,
        "lease_duration_months": 6,
        "owner_name": "BZU Area Hostel", "owner_email": "bzu.hostel.mtn@rooms.pk", "owner_phone": "061-2345678",
    },
    {
        "city": "Multan",
        "title": "Single Furnished Room — Cantt Multan",
        "description": "Nice furnished room in Multan Cantt area. Shared with one other professional. Independent bathroom, AC, inverter. Very peaceful environment.",
        "location": "Multan",
        "rent_price": 13000,
        "room_type": "Single",
        "bedrooms": 1,
        "bathrooms": 1,
        "amenities": ["Furnished", "AC", "Inverter Backup", "Attached Bath", "WiFi"],
        "smoking_allowed": False,
        "pets_allowed": False,
        "lease_duration_months": 6,
        "owner_name": "Naeem Akhtar", "owner_email": "naeem.rooms.mtn@rooms.pk", "owner_phone": "0303-9876543",
    },

    # ── Faisalabad ────────────────────────────────────────────────────────
    {
        "city": "Faisalabad",
        "title": "Student Hostel Near UAF — Faisalabad",
        "description": "Hostel near University of Agriculture Faisalabad (UAF). 2-bed shared rooms, large study hall, mess facility, prayer area, sports ground access.",
        "location": "Faisalabad",
        "rent_price": 4500,
        "room_type": "Shared",
        "bedrooms": 1,
        "bathrooms": 1,
        "amenities": ["Meals Available", "Study Hall", "Prayer Area", "Sports Facilities", "WiFi"],
        "smoking_allowed": False,
        "pets_allowed": False,
        "lease_duration_months": 12,
        "owner_name": "UAF Area Hostel", "owner_email": "uaf.hostel.fsd@rooms.pk", "owner_phone": "041-2345678",
    },
    {
        "city": "Faisalabad",
        "title": "Master Room — Susan Road Faisalabad",
        "description": "Large master room with attached bath in a well-kept house on Susan Road. Includes lounge access, rooftop, fast internet, inverter backup.",
        "location": "Faisalabad",
        "rent_price": 16000,
        "room_type": "Master",
        "bedrooms": 1,
        "bathrooms": 1,
        "amenities": ["Attached Bath", "Furnished", "WiFi", "Inverter Backup", "Rooftop"],
        "smoking_allowed": False,
        "pets_allowed": False,
        "lease_duration_months": 6,
        "owner_name": "Irfan Shahzad", "owner_email": "irfan.rooms.fsd@rooms.pk", "owner_phone": "0301-2345678",
    },

    # ── Peshawar ──────────────────────────────────────────────────────────
    {
        "city": "Peshawar",
        "title": "Male Hostel Near UET Peshawar",
        "description": "Established hostel 2 km from UET Peshawar. Shared rooms for 3. Separate study zone, volleyball court, warden available. Monthly electricity included.",
        "location": "Peshawar",
        "rent_price": 5500,
        "room_type": "Shared",
        "bedrooms": 1,
        "bathrooms": 1,
        "amenities": ["WiFi", "Study Hall", "Sports Facilities", "Generator Backup"],
        "smoking_allowed": False,
        "pets_allowed": False,
        "lease_duration_months": 12,
        "owner_name": "Peshawar Hostel PW", "owner_email": "pwr.hostel.psh@rooms.pk", "owner_phone": "091-2345678",
    },
    {
        "city": "Peshawar",
        "title": "Single Room — Hayatabad Phase 5",
        "description": "Clean single room in Hayatabad Phase 5 with one professional flatmate. Solar electricity, Fiber WiFi, furnished, very safe gated area.",
        "location": "Peshawar",
        "rent_price": 15000,
        "room_type": "Single",
        "bedrooms": 1,
        "bathrooms": 1,
        "amenities": ["Furnished", "WiFi", "Solar Electricity", "Gated Community"],
        "smoking_allowed": False,
        "pets_allowed": False,
        "lease_duration_months": 6,
        "owner_name": "Kamran Shah", "owner_email": "kamran.rooms.psh@rooms.pk", "owner_phone": "0333-9087654",
    },
]

# ---------------------------------------------------------------------------

SYSTEM_EMAIL = "system@roommate-ai.internal"


def run():
    from backend.app import create_app
    from backend.database import db
    from backend.models.user import User
    from backend.models.room import Room
    from datetime import date, timedelta

    # Use production only when DATABASE_URL points to a real Postgres server.
    # A sqlite:// value in DATABASE_URL (common in local .env) must use development config.
    db_url = os.environ.get("DATABASE_URL", "")
    env = "production" if (db_url and db_url.startswith(("postgres://", "postgresql://"))) else "development"
    app = create_app(env)

    with app.app_context():
        db.create_all()

        if args.clear:
            print("Clearing all existing rooms…")
            Room.query.delete()
            db.session.commit()
            print("  Done.")

        # Get or create system user
        system_user = User.query.filter_by(email=SYSTEM_EMAIL).first()
        if not system_user:
            system_user = User(
                email=SYSTEM_EMAIL,
                full_name="RoomMate AI",
                city="System",
                is_active=True,
            )
            system_user.set_password(os.urandom(24).hex())
            db.session.add(system_user)
            db.session.commit()
            print("Created system user.")

        saved = 0
        skipped = 0

        for r in ROOMS:
            if args.city and r["city"].lower() != args.city.lower():
                continue

            # Skip duplicates
            existing = Room.query.filter_by(title=r["title"], location=r["location"]).first()
            if existing:
                skipped += 1
                continue

            # Assign a rotating owner — use the system user as fallback
            owner_email = r.get("owner_email", SYSTEM_EMAIL)
            owner = User.query.filter_by(email=owner_email).first()
            if not owner:
                owner = User(
                    email=owner_email,
                    full_name=r.get("owner_name", "Room Owner"),
                    city=r["city"],
                    phone=r.get("owner_phone"),
                    is_active=True,
                )
                owner.set_password(os.urandom(16).hex())
                db.session.add(owner)
                db.session.flush()  # get owner_id

            room = Room(
                owner_id=owner.user_id,
                title=r["title"],
                description=r["description"],
                location=r["location"],
                rent_price=r["rent_price"],
                room_type=r["room_type"],
                bedrooms=r.get("bedrooms", 1),
                bathrooms=r.get("bathrooms", 1),
                amenities=r.get("amenities", []),
                images=[],   # no images needed
                smoking_allowed=r.get("smoking_allowed", False),
                pets_allowed=r.get("pets_allowed", False),
                is_available=True,
                available_from=date.today(),
                lease_duration_months=r.get("lease_duration_months", 6),
            )
            db.session.add(room)
            saved += 1

        db.session.commit()
        total = Room.query.filter_by(is_available=True).count()
        print(f"Seeded {saved} new rooms ({skipped} skipped as duplicates).")
        print(f"Total available rooms in DB: {total}")


if __name__ == "__main__":
    run()
