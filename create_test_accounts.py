"""
Script to create 20 test accounts with varied preferences for testing the roommate matching system
"""
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database import db
from backend.models.user import User
from backend.models.preference import UserPreference
from backend.models.room import Room
from backend.models.score import CompatibilityScore
from backend.models.match import Recommendation
from backend.app import create_app
from datetime import datetime, date
import bcrypt
import random

app = create_app()

# Test user data with varied profiles
TEST_USERS = [
    {"full_name": "John Smith", "email": "john@test.com", "gender": "M", "city": "Downtown", "bio": "Graduate student looking for a quiet roommate"},
    {"full_name": "Sarah Johnson", "email": "sarah@test.com", "gender": "F", "city": "Midtown", "bio": "Software engineer, work from home"},
    {"full_name": "Mike Chen", "email": "mike@test.com", "gender": "M", "city": "University District", "bio": "Medical student, early riser"},
    {"full_name": "Emily Davis", "email": "emily@test.com", "gender": "F", "city": "Downtown", "bio": "Marketing manager, social butterfly"},
    {"full_name": "Alex Kim", "email": "alex@test.com", "gender": "Other", "city": "Tech Hub", "bio": "Art student, night owl"},
    {"full_name": "Jessica Brown", "email": "jessica@test.com", "gender": "F", "city": "Suburbs", "bio": "Nurse, varying schedule"},
    {"full_name": "David Wilson", "email": "david@test.com", "gender": "M", "city": "Downtown", "bio": "Accountant, quiet and organized"},
    {"full_name": "Lisa Martinez", "email": "lisa@test.com", "gender": "F", "city": "University District", "bio": "Undergraduate, loves cooking"},
    {"full_name": "Chris Taylor", "email": "chris@test.com", "gender": "M", "city": "Tech Hub", "bio": "Remote developer, flexible schedule"},
    {"full_name": "Amanda White", "email": "amanda@test.com", "gender": "F", "city": "Suburbs", "bio": "PhD candidate, bookworm"},
    {"full_name": "Ryan Garcia", "email": "ryan@test.com", "gender": "M", "city": "Midtown", "bio": "Sales rep, travels often"},
    {"full_name": "Michelle Lee", "email": "michelle@test.com", "gender": "F", "city": "Downtown", "bio": "MBA student, fitness enthusiast"},
    {"full_name": "Brandon Moore", "email": "brandon@test.com", "gender": "M", "city": "Suburbs", "bio": "Teacher, home by 5pm"},
    {"full_name": "Rachel Adams", "email": "rachel@test.com", "gender": "F", "city": "Tech Hub", "bio": "Graphic designer, creative space needed"},
    {"full_name": "Kevin Thompson", "email": "kevin@test.com", "gender": "M", "city": "University District", "bio": "Engineering student, gamer"},
    {"full_name": "Stephanie Clark", "email": "stephanie@test.com", "gender": "F", "city": "Downtown", "bio": "Lawyer, long work hours"},
    {"full_name": "Daniel Rodriguez", "email": "daniel@test.com", "gender": "M", "city": "Midtown", "bio": "Chef, late night shifts"},
    {"full_name": "Nicole Harris", "email": "nicole@test.com", "gender": "F", "city": "University District", "bio": "Nursing student, needs quiet"},
    {"full_name": "Jason Lewis", "email": "jason@test.com", "gender": "M", "city": "Tech Hub", "bio": "Consultant, often working remotely"},
    {"full_name": "Megan Walker", "email": "megan@test.com", "gender": "F", "city": "Suburbs", "bio": "Freshman, first time living away from home"},
    # ===== CONFLICT-INDUCING TEST USERS (21-40) =====
    # Heavy smoker, messy, loud, low budget
    {"full_name": "Rick Grimes", "email": "rick@test.com", "gender": "M", "city": "Downtown", "bio": "Chain smoker, DJ on weekends, parties every night"},
    # Non-smoker with asthma, ultra-clean, needs silence
    {"full_name": "Clara Oswald", "email": "clara@test.com", "gender": "F", "city": "Downtown", "bio": "Has severe asthma, needs absolutely smoke-free environment"},
    # Owns 3 cats and a dog, relaxed about cleaning
    {"full_name": "Pete Litter", "email": "pete@test.com", "gender": "M", "city": "Midtown", "bio": "Animal rescue volunteer, owns 3 cats and a dog"},
    # Severe pet allergies, very clean
    {"full_name": "Allergy Anne", "email": "anne@test.com", "gender": "F", "city": "Midtown", "bio": "Life-threatening pet allergies, needs sterile environment"},
    # Ultra high budget, luxury seeker
    {"full_name": "Rich Richman", "email": "rich@test.com", "gender": "M", "city": "Downtown", "bio": "Investment banker, only premium living spaces"},
    # Extreme low budget
    {"full_name": "Penny Pincher", "email": "penny@test.com", "gender": "F", "city": "Downtown", "bio": "Minimum wage worker, every dollar counts"},
    # Night shift worker, sleeps all day
    {"full_name": "Nate Nightowl", "email": "nate@test.com", "gender": "M", "city": "Tech Hub", "bio": "ER doctor, works midnight to 8am, sleeps during the day"},
    # 5am riser, loud morning routine
    {"full_name": "Dawn Riser", "email": "dawn@test.com", "gender": "F", "city": "Tech Hub", "bio": "Runs at 5am, blends smoothies at 6am, yoga at 7am"},
    # Extreme party person, messy, smoker
    {"full_name": "Dustin Rager", "email": "dustin@test.com", "gender": "M", "city": "University District", "bio": "Frat house president, throws parties every weekend"},
    # Library-quiet studier, neat freak
    {"full_name": "Quiet Quinn", "email": "quinn@test.com", "gender": "F", "city": "University District", "bio": "PhD candidate, needs absolute silence for research, OCD about cleanliness"},
    # Smoker + pet owner + night shift + messy + loud
    {"full_name": "Max Chaos", "email": "max@test.com", "gender": "M", "city": "Suburbs", "bio": "Freelancer with 2 loud parrots, smokes indoors, night person"},
    # Non-smoker + no pets + day shift + spotless + quiet
    {"full_name": "Zen Harmony", "email": "zen@test.com", "gender": "Other", "city": "Suburbs", "bio": "Meditation instructor, needs perfect silence and purity"},
    # Only wants female roommates, high budget
    {"full_name": "Tina Exclusive", "email": "tina@test.com", "gender": "F", "city": "Midtown", "bio": "Prefers female-only living arrangement, safety conscious"},
    # Only wants male roommates, low budget
    {"full_name": "Brad Bro", "email": "brad@test.com", "gender": "M", "city": "Midtown", "bio": "Gym bro looking for male roommates only"},
    # Wants shared room but huge budget mismatch
    {"full_name": "Confused Carl", "email": "carl@test.com", "gender": "M", "city": "Downtown", "bio": "Wants shared room to save money but has luxury tastes"},
    # Student with erratic schedule, pet lover, smoker
    {"full_name": "Wildcard Wendy", "email": "wendy@test.com", "gender": "F", "city": "University District", "bio": "Art student, paints at 3am, has a ferret, smokes herbs"},
    # Rigid 9-5, hates pets, hates smoke, very clean
    {"full_name": "Strict Steve", "email": "steve@test.com", "gender": "M", "city": "University District", "bio": "Accountant, everything by the book, zero tolerance for mess"},
    # Extremely messy, extremely loud, low budget
    {"full_name": "Sloppy Sam", "email": "sam@test.com", "gender": "M", "city": "Suburbs", "bio": "Band drummer, practices at home, dishes pile up for weeks"},
    # Neat freak, needs premium quiet space
    {"full_name": "Pristine Priya", "email": "priya@test.com", "gender": "F", "city": "Suburbs", "bio": "Surgeon, needs spotless home, absolute quiet for sleep before shifts"},
    # Smoker + pet owner looking for cheap place
    {"full_name": "Rogue Remy", "email": "remy@test.com", "gender": "Other", "city": "Tech Hub", "bio": "Street musician with a huge dog, chain smoker, budget tight"},
]

# Preference variations matching the model enums
CLEANLINESS = ["Very Clean", "Clean", "Average", "Relaxed"]
SCHEDULES = ["9-5 Job", "Night Shift", "Student", "Flexible"]
ROOM_TYPES = ["Single", "Shared", "Any"]
GENDER_PREFS = ["M", "F", "Any"]

# ===== HARDCODED CONFLICT PREFERENCES =====
# These override random preferences for conflict-inducing users to ensure agents detect conflicts
CONFLICT_PREFERENCES = {
    "rick@test.com":    {"budget_min": 300, "budget_max": 600, "cleanliness": "Relaxed", "schedule": "Night Shift", "smoking_ok": True, "pets_ok": True, "noise_tolerance": 10, "room_type": "Shared", "gender_pref": "Any", "location": "Downtown"},
    "clara@test.com":   {"budget_min": 800, "budget_max": 1500, "cleanliness": "Very Clean", "schedule": "9-5 Job", "smoking_ok": False, "pets_ok": False, "noise_tolerance": 1, "room_type": "Single", "gender_pref": "F", "location": "Downtown"},
    "pete@test.com":    {"budget_min": 500, "budget_max": 900, "cleanliness": "Relaxed", "schedule": "Flexible", "smoking_ok": True, "pets_ok": True, "noise_tolerance": 8, "room_type": "Shared", "gender_pref": "Any", "location": "Midtown"},
    "anne@test.com":    {"budget_min": 700, "budget_max": 1400, "cleanliness": "Very Clean", "schedule": "9-5 Job", "smoking_ok": False, "pets_ok": False, "noise_tolerance": 2, "room_type": "Single", "gender_pref": "F", "location": "Midtown"},
    "rich@test.com":    {"budget_min": 2000, "budget_max": 5000, "cleanliness": "Very Clean", "schedule": "9-5 Job", "smoking_ok": False, "pets_ok": False, "noise_tolerance": 3, "room_type": "Single", "gender_pref": "Any", "location": "Downtown"},
    "penny@test.com":   {"budget_min": 200, "budget_max": 450, "cleanliness": "Average", "schedule": "Flexible", "smoking_ok": True, "pets_ok": True, "noise_tolerance": 7, "room_type": "Shared", "gender_pref": "Any", "location": "Downtown"},
    "nate@test.com":    {"budget_min": 800, "budget_max": 1600, "cleanliness": "Clean", "schedule": "Night Shift", "smoking_ok": False, "pets_ok": False, "noise_tolerance": 1, "room_type": "Single", "gender_pref": "M", "location": "Tech Hub"},
    "dawn@test.com":    {"budget_min": 700, "budget_max": 1300, "cleanliness": "Very Clean", "schedule": "9-5 Job", "smoking_ok": False, "pets_ok": True, "noise_tolerance": 8, "room_type": "Any", "gender_pref": "F", "location": "Tech Hub"},
    "dustin@test.com":  {"budget_min": 400, "budget_max": 700, "cleanliness": "Relaxed", "schedule": "Student", "smoking_ok": True, "pets_ok": True, "noise_tolerance": 10, "room_type": "Shared", "gender_pref": "M", "location": "University District"},
    "quinn@test.com":   {"budget_min": 900, "budget_max": 1800, "cleanliness": "Very Clean", "schedule": "Student", "smoking_ok": False, "pets_ok": False, "noise_tolerance": 1, "room_type": "Single", "gender_pref": "F", "location": "University District"},
    "max@test.com":     {"budget_min": 300, "budget_max": 550, "cleanliness": "Relaxed", "schedule": "Night Shift", "smoking_ok": True, "pets_ok": True, "noise_tolerance": 10, "room_type": "Any", "gender_pref": "Any", "location": "Suburbs"},
    "zen@test.com":     {"budget_min": 1000, "budget_max": 2000, "cleanliness": "Very Clean", "schedule": "9-5 Job", "smoking_ok": False, "pets_ok": False, "noise_tolerance": 1, "room_type": "Single", "gender_pref": "Any", "location": "Suburbs"},
    "tina@test.com":    {"budget_min": 1200, "budget_max": 2500, "cleanliness": "Clean", "schedule": "9-5 Job", "smoking_ok": False, "pets_ok": False, "noise_tolerance": 3, "room_type": "Single", "gender_pref": "F", "location": "Midtown"},
    "brad@test.com":    {"budget_min": 350, "budget_max": 600, "cleanliness": "Average", "schedule": "Flexible", "smoking_ok": True, "pets_ok": True, "noise_tolerance": 9, "room_type": "Shared", "gender_pref": "M", "location": "Midtown"},
    "carl@test.com":    {"budget_min": 1500, "budget_max": 3500, "cleanliness": "Very Clean", "schedule": "Flexible", "smoking_ok": False, "pets_ok": False, "noise_tolerance": 4, "room_type": "Shared", "gender_pref": "Any", "location": "Downtown"},
    "wendy@test.com":   {"budget_min": 300, "budget_max": 500, "cleanliness": "Relaxed", "schedule": "Student", "smoking_ok": True, "pets_ok": True, "noise_tolerance": 9, "room_type": "Shared", "gender_pref": "Any", "location": "University District"},
    "steve@test.com":   {"budget_min": 900, "budget_max": 1600, "cleanliness": "Very Clean", "schedule": "9-5 Job", "smoking_ok": False, "pets_ok": False, "noise_tolerance": 2, "room_type": "Single", "gender_pref": "M", "location": "University District"},
    "sam@test.com":     {"budget_min": 250, "budget_max": 500, "cleanliness": "Relaxed", "schedule": "Flexible", "smoking_ok": True, "pets_ok": True, "noise_tolerance": 10, "room_type": "Shared", "gender_pref": "Any", "location": "Suburbs"},
    "priya@test.com":   {"budget_min": 1500, "budget_max": 3000, "cleanliness": "Very Clean", "schedule": "Night Shift", "smoking_ok": False, "pets_ok": False, "noise_tolerance": 1, "room_type": "Single", "gender_pref": "F", "location": "Suburbs"},
    "remy@test.com":    {"budget_min": 200, "budget_max": 400, "cleanliness": "Relaxed", "schedule": "Flexible", "smoking_ok": True, "pets_ok": True, "noise_tolerance": 10, "room_type": "Any", "gender_pref": "Any", "location": "Tech Hub"},
}

def create_test_data():
    with app.app_context():
        print("Creating test users and preferences...")
        
        created_users = []
        
        for i, user_data in enumerate(TEST_USERS):
            # Check if user already exists
            existing = User.query.filter_by(email=user_data["email"]).first()
            if existing:
                # Fix password hash if it was created with werkzeug instead of bcrypt
                new_hash = bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt(rounds=10)).decode('utf-8')
                existing.password_hash = new_hash
                print(f"  User {user_data['email']} already exists, updated password hash")
                created_users.append(existing)
                continue
            
            # Create user
            user = User(
                email=user_data["email"],
                password_hash=bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt(rounds=10)).decode('utf-8'),
                full_name=user_data["full_name"],
                phone=f"555{str(i).zfill(7)}",
                profile_picture=None,
                bio=user_data["bio"],
                gender=user_data["gender"],
                city=user_data["city"],
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(user)
            db.session.flush()  # Get user_id
            
            # Create preferences - use hardcoded conflict values if available, else random
            cp = CONFLICT_PREFERENCES.get(user_data["email"])
            pref = UserPreference(
                user_id=user.user_id,
                budget_min=cp["budget_min"] if cp else random.randint(400, 800),
                budget_max=cp["budget_max"] if cp else random.randint(1000, 2000),
                preferred_location=cp["location"] if cp else random.choice(["Downtown", "Suburbs", "University District", "Tech Hub", "Midtown"]),
                gender_preference=cp["gender_pref"] if cp else random.choice(GENDER_PREFS),
                age_min=18,
                age_max=35,
                cleanliness_level=cp["cleanliness"] if cp else random.choice(CLEANLINESS),
                schedule=cp["schedule"] if cp else random.choice(SCHEDULES),
                smoking_ok=cp["smoking_ok"] if cp else random.choice([True, False]),
                pets_ok=cp["pets_ok"] if cp else random.choice([True, False]),
                noise_tolerance=cp["noise_tolerance"] if cp else random.randint(1, 10),
                preferred_room_type=cp["room_type"] if cp else random.choice(ROOM_TYPES),
                lease_duration_months=random.choice([6, 12]),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(pref)
            
            created_users.append(user)
            print(f"  Created user: {user_data['full_name']} ({user_data['email']})")
        
        db.session.commit()
        print(f"\n[OK] Created {len(created_users)} users with preferences")
        
        # Create some compatibility scores between users
        print("\nGenerating compatibility scores...")
        scores_created = 0
        for i, user_a in enumerate(created_users):
            for user_b in created_users[i+1:]:
                # Check if score already exists
                existing_score = CompatibilityScore.query.filter(
                    ((CompatibilityScore.user_a_id == user_a.user_id) & 
                     (CompatibilityScore.user_b_id == user_b.user_id)) |
                    ((CompatibilityScore.user_a_id == user_b.user_id) & 
                     (CompatibilityScore.user_b_id == user_a.user_id))
                ).first()
                
                if existing_score:
                    continue
                
                # Generate random but realistic compatibility scores
                lifestyle = random.randint(40, 100)
                schedule = random.randint(40, 100)
                budget = random.randint(50, 100)
                habits = random.randint(40, 100)
                age_match = random.randint(60, 100)
                overall = int((lifestyle * 0.25 + schedule * 0.2 + budget * 0.2 + habits * 0.2 + age_match * 0.15))
                
                score = CompatibilityScore(
                    user_a_id=user_a.user_id,
                    user_b_id=user_b.user_id,
                    overall_score=overall,
                    lifestyle_score=lifestyle,
                    schedule_score=schedule,
                    budget_score=budget,
                    habits_score=habits,
                    age_match_score=age_match,
                    computed_at=datetime.utcnow()
                )
                db.session.add(score)
                scores_created += 1
        
        db.session.commit()
        print(f"[OK] Created {scores_created} compatibility scores")
        
        # Create recommendations for each user (top matches)
        print("\nGenerating recommendations...")
        recs_created = 0
        for user in created_users:
            # Get top 5 matches for this user
            top_scores = CompatibilityScore.query.filter(
                (CompatibilityScore.user_a_id == user.user_id) | 
                (CompatibilityScore.user_b_id == user.user_id)
            ).order_by(CompatibilityScore.overall_score.desc()).limit(5).all()
            
            for score in top_scores:
                # Get the other user's ID
                match_id = score.user_b_id if score.user_a_id == user.user_id else score.user_a_id
                
                # Check if recommendation already exists
                existing_rec = Recommendation.query.filter_by(
                    requester_id=user.user_id,
                    match_id=match_id
                ).first()
                
                if existing_rec:
                    continue
                
                rec = Recommendation(
                    requester_id=user.user_id,
                    match_type='roommate',
                    match_id=match_id,
                    match_score=score.overall_score,
                    explanation=f"High compatibility match based on lifestyle and schedule preferences",
                    conflict_warnings='[]',
                    created_at=datetime.utcnow()
                )
                db.session.add(rec)
                recs_created += 1
        
        db.session.commit()
        print(f"[OK] Created {recs_created} recommendations")
        
        # Create some room listings (original + conflict-testing rooms)
        print("\nCreating room listings...")
        rooms_data = [
            {"title": "Cozy Studio Downtown", "room_type": "Single", "rent": 1200, "location": "Downtown", "smoking": False, "pets": False},
            {"title": "Shared Apartment Near Campus", "room_type": "Shared", "rent": 650, "location": "University District", "smoking": False, "pets": True},
            {"title": "Master Bedroom with Bath", "room_type": "Master", "rent": 1500, "location": "Midtown", "smoking": False, "pets": False},
            {"title": "Budget Friendly Room", "room_type": "Single", "rent": 500, "location": "Suburbs", "smoking": True, "pets": True},
            {"title": "Modern Shared Space", "room_type": "Shared", "rent": 750, "location": "Tech Hub", "smoking": False, "pets": False},
            # Conflict-inducing rooms
            {"title": "Smoker's Paradise Loft", "room_type": "Shared", "rent": 400, "location": "Downtown", "smoking": True, "pets": True},
            {"title": "Luxury Penthouse Suite", "room_type": "Single", "rent": 4500, "location": "Downtown", "smoking": False, "pets": False},
            {"title": "Ultra Cheap Shared Bunk", "room_type": "Shared", "rent": 250, "location": "Suburbs", "smoking": True, "pets": True},
            {"title": "Pet-Friendly Haven", "room_type": "Single", "rent": 900, "location": "Midtown", "smoking": False, "pets": True},
            {"title": "Sterile No-Pet Zone", "room_type": "Single", "rent": 1100, "location": "Midtown", "smoking": False, "pets": False},
            {"title": "Party Pad Shared Room", "room_type": "Shared", "rent": 350, "location": "University District", "smoking": True, "pets": True},
            {"title": "Quiet Study Room", "room_type": "Single", "rent": 1400, "location": "University District", "smoking": False, "pets": False},
            {"title": "Night Worker's Retreat", "room_type": "Single", "rent": 800, "location": "Tech Hub", "smoking": False, "pets": False},
            {"title": "Smoke & Pet Friendly Shared", "room_type": "Shared", "rent": 300, "location": "Suburbs", "smoking": True, "pets": True},
            {"title": "Premium Executive Room", "room_type": "Master", "rent": 3500, "location": "Downtown", "smoking": False, "pets": False},
        ]
        
        rooms_created = 0
        for i, room_data in enumerate(rooms_data):
            owner = created_users[i % len(created_users)]
            
            existing_room = Room.query.filter_by(
                owner_id=owner.user_id,
                title=room_data["title"]
            ).first()
            
            if existing_room:
                continue
                
            room = Room(
                owner_id=owner.user_id,
                title=room_data["title"],
                description=f"A great {room_data['room_type'].lower()} room in {room_data['location']}",
                room_type=room_data["room_type"],
                rent_price=room_data["rent"],
                location=room_data["location"],
                bedrooms=random.randint(1, 3),
                bathrooms=random.choice([1.0, 1.5, 2.0]),
                amenities=["WiFi", "Laundry", "Kitchen"],
                smoking_allowed=room_data.get("smoking", random.choice([True, False])),
                pets_allowed=room_data.get("pets", random.choice([True, False])),
                images=["placeholder.jpg"],
                is_available=True,
                available_from=date(2026, 3, 1),
                lease_duration_months=12,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(room)
            rooms_created += 1
        
        db.session.commit()
        print(f"[OK] Created {rooms_created} room listings")
        
        print("\n" + "="*50)
        print("TEST DATA CREATION COMPLETE!")
        print("="*50)
        print("\nYou can now log in with any of these accounts:")
        print("Password for all: password123")
        print("\nExample accounts:")
        for user in created_users[:5]:
            print(f"  - {user.email}")
        print(f"  ... and {len(created_users) - 5} more")

if __name__ == "__main__":
    create_test_data()
