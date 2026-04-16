# Getting Started Guide
## AI-Powered Roommate Matching System

This guide walks you through setting up and running the project from scratch, understanding each component, and navigating the codebase.

---

## Table of Contents
1. [Prerequisites](#1-prerequisites)
2. [Installation](#2-installation)
3. [Environment Variables](#3-environment-variables)
4. [Database Setup](#4-database-setup)
5. [Seeding Room Data](#5-seeding-room-data)
6. [Running the Application](#6-running-the-application)
7. [Project Structure Explained](#7-project-structure-explained)
8. [Understanding the Flow](#8-understanding-the-flow)
9. [Key Files to Read First](#9-key-files-to-read-first)
10. [Common Troubleshooting](#10-common-troubleshooting)

---

## 1. Prerequisites

| Requirement | Version | Purpose |
|---|---|---|
| Python | 3.10+ | Backend runtime |
| pip | Latest | Package installer |
| Git | Any | Version control |
| Browser | Chrome/Firefox | Running the frontend |

Optional (for production only):
- PostgreSQL / Neon account — the app uses SQLite locally

---

## 2. Installation

```bash
# Navigate to project folder
cd roommate-matching-system

# Create a virtual environment (keeps dependencies isolated)
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install all Python packages
pip install -r requirements.txt
```

---

## 3. Environment Variables

Copy the example file and fill it in:

```bash
copy .env.example .env      # Windows
cp .env.example .env        # Mac/Linux
```

Open `.env` and set:

```env
# Flask security keys — use any random string locally
SECRET_KEY=dev-secret-key
JWT_SECRET_KEY=dev-jwt-secret

# Database — SQLite for local development (no setup needed)
DATABASE_URL=sqlite:///./database/roommate_system.db

# Google Gemini AI — needed for AI explanations in match results
# Get from: https://aistudio.google.com/app/apikey
GOOGLE_API_KEY=AIza...your_key_here

# Flask environment
FLASK_ENV=development
```

> **Without `GOOGLE_API_KEY`:** The app still runs. Roommate matching, room
> scoring, and all features work. Only the AI natural-language explanations
> ("Why are these two users a good match?") will fall back to a rule-based
> summary instead of Gemini output.

---

## 4. Database Setup

The database is created automatically when Flask starts. But if you want to set it up manually:

```bash
python -c "
from dotenv import load_dotenv; load_dotenv()
from backend.app import create_app
app = create_app('development')
with app.app_context():
    from backend.database import db
    db.create_all()
    print('Tables created.')
"
```

**If you are upgrading from an older version** (adding new Room columns):
```bash
python migrate_db.py
```
This safely adds the new columns (`address`, `latitude`, `longitude`, `place_id`, `google_rating`, `google_maps_url`) to the existing `rooms` table without touching any data.

### Load survey users (327 real IUB profiles)

```bash
# Local SQLite
python load_survey_data.py

# Production Neon/PostgreSQL
DATABASE_URL="postgresql+pg8000://..." python seed_prod.py
```

---

## 5. Seeding Room Data

The app comes with a seed script that creates 23 realistic Pakistani room listings across 8 cities. No internet or API key needed.

```bash
# Add rooms (skips duplicates automatically)
python seed_rooms.py

# Wipe all rooms and start fresh
python seed_rooms.py --clear

# Seed only one city
python seed_rooms.py --city Lahore
```

Cities covered: **Bahawalpur, Islamabad, Lahore, Karachi, Rawalpindi, Multan, Faisalabad, Peshawar**

Room types: Single rooms, Shared hostels, Master bedrooms
Price range: PKR 4,000 – 45,000/month

---

## 6. Running the Application

```bash
# From the roommate-matching-system/ folder with venv active:
python backend/app.py
```

Open your browser at: **http://localhost:5000**

You should see the landing page. From there:
1. **Register** an account
2. Fill in the **Preferences** form (budget, lifestyle, schedule, etc.)
3. Go to **Dashboard** → trigger AI roommate matching
4. Go to **Rooms** → browse rooms with compatibility scores
5. Click **"Find My Best Rooms (AI)"** → AI pipeline ranks rooms for you

---

## 7. Project Structure Explained

```
roommate-matching-system/
│
├── backend/                         ← All Python server-side code
│   ├── app.py                       ← Flask app factory (start here)
│   ├── config.py                    ← Dev / prod config classes
│   ├── database.py                  ← SQLAlchemy db object
│   │
│   ├── agents/                      ← The 6 AI agents
│   │   ├── base_agent.py            ← Abstract base all agents extend
│   │   ├── user_profiling_agent.py  ← Validates user profile completeness
│   │   ├── preference_analysis_agent.py  ← Converts prefs → vectors
│   │   ├── compatibility_scoring_agent.py ← Scores user pairs
│   │   ├── room_matching_agent.py   ← Scores rooms against user prefs
│   │   ├── conflict_detection_agent.py   ← Flags hard/soft blockers
│   │   ├── recommendation_engine_agent.py ← Ranks + Gemini explanations
│   │   └── agent_orchestrator.py    ← Controls the full pipeline
│   │
│   ├── models/                      ← SQLAlchemy ORM models
│   │   ├── user.py                  ← User accounts
│   │   ├── preference.py            ← UserPreference + PreferenceVector
│   │   ├── room.py                  ← Room listings (incl. Google Places fields)
│   │   ├── score.py                 ← CompatibilityScore
│   │   ├── match.py                 ← Recommendation
│   │   ├── conflict.py              ← ConflictLog
│   │   └── audit.py                 ← AuditLog
│   │
│   ├── routes/                      ← REST API endpoints (Flask blueprints)
│   │   ├── auth.py                  ← /auth/register, /auth/login, /auth/verify
│   │   ├── users.py                 ← /users/<id>
│   │   ├── preferences.py           ← /preferences/user/<id>
│   │   ├── rooms.py                 ← /rooms, /rooms/matched, /rooms/search
│   │   ├── matching.py              ← /matches/compute, /matches/user/<id>
│   │   ├── recommendations.py       ← /recommendations/user/<id>
│   │   └── orchestrate.py           ← /orchestrate/matches, /orchestrate/rooms
│   │
│   └── services/                    ← (empty — no external services)
│
├── frontend/                        ← Static HTML/CSS/JS pages
│   ├── index.html                   ← Landing page
│   ├── register.html                ← Registration form
│   ├── login.html                   ← Login form
│   ├── dashboard.html               ← Main dashboard after login
│   ├── preferences.html             ← Preferences form (budget, lifestyle…)
│   ├── matches.html                 ← Roommate match results
│   ├── rooms.html                   ← Room listings + AI matching
│   ├── profile.html                 ← User profile page
│   ├── settings.html                ← Account settings
│   ├── ai-agents.html               ← Agent activity/status page
│   ├── js/
│   │   ├── api.js                   ← Central API client (all HTTP calls)
│   │   ├── auth.js                  ← JWT + auth helpers
│   │   └── main.js                  ← Shared UI utilities
│   └── css/
│       ├── style.css                ← Main styles
│       └── design-system.css        ← Design tokens (Airbnb-style light theme)
│
├── database/
│   └── roommate_system.db           ← SQLite file (git-ignored in prod)
│
├── seed_rooms.py                    ← Seeds 23 Pakistani room listings (no API needed)
├── seed_prod.py                     ← Seeds 327 IUB survey users (production)
├── load_survey_data.py              ← Loads survey Excel → local DB
├── migrate_db.py                    ← Adds new Room columns to existing DB
├── requirements.txt                 ← Python dependencies
├── vercel.json                      ← Vercel deployment routing config
└── .env                             ← Local environment variables (git-ignored)
```

---

## 8. Understanding the Flow

### Roommate Matching Flow

```
User clicks "Find Matches" on Dashboard
    ↓
POST /orchestrate/matches
    ↓
Agent Orchestrator runs the pipeline:
    1. User Profiling Agent
       → checks user profile is complete
    2. Preference Analysis Agent
       → converts prefs to a numerical vector [0.5, 0.8, 0.3, ...]
    3. Compatibility Scoring Agent
       → computes cosine similarity + sub-scores for every other user
          overall = 0.3×similarity + 0.2×lifestyle + 0.2×schedule
                  + 0.15×budget + 0.15×habits
    4. Conflict Detection Agent
       → flags hard blockers (smoking, pets, budget gap)
    5. Recommendation Engine Agent
       → ranks by score, calls Gemini to write explanation
       → stores in recommendations table
    ↓
Frontend receives ranked list with scores + explanations
```

### Room Matching Flow

```
User opens Rooms page
    ↓
GET /rooms/matched
    ↓
Backend:
    1. Loads user's UserPreference
    2. Queries all available rooms
    3. Calls room.get_compatibility_score(prefs) for each
    4. Returns sorted by score desc
    ↓
Frontend renders room cards with "82% match" badges

User clicks "Find My Best Rooms (AI)"
    ↓
POST /orchestrate/rooms
    ↓
Room Matching Agent runs:
    → filters by budget, location, smoking, pets
    → scores remaining rooms
    → calls Gemini for a search summary
    ↓
Frontend injects AI-matched section at top of grid
```

### Scoring Formula

**Roommate compatibility score (0–100):**
```
score = cosine_similarity × 100 × 0.30
      + lifestyle_score           × 0.20
      + schedule_score            × 0.20
      + budget_score              × 0.15
      + habits_score              × 0.15
```

**Room compatibility score (0–100):**
```
score = budget_overlap_points   (max 40)
      + location_match_points   (max 30)
      + room_type_match_points  (max 20)
      + amenity_coverage_points (max 10)
```

---

## 9. Key Files to Read First

If you're studying the code, start in this order:

1. **`backend/app.py`** — How Flask is initialised and all blueprints registered
2. **`backend/agents/agent_orchestrator.py`** — The pipeline controller
3. **`backend/agents/compatibility_scoring_agent.py`** — Core scoring math
4. **`backend/models/room.py`** — Room model with `get_compatibility_score()`
5. **`backend/routes/rooms.py`** — Room API endpoints incl. `/matched`
6. **`frontend/js/api.js`** — Every API call the frontend makes
7. **`frontend/rooms.html`** — The complete room listing UI + AI matching

---

## 10. Common Troubleshooting

**App won't start — import error**
```bash
# Make sure venv is active and packages installed
pip install -r requirements.txt
```

**Database error on first run**
```bash
# Run the migration to create/update all tables
python migrate_db.py
```

**No rooms showing**
```bash
# Seed the database
python seed_rooms.py
```

**AI explanations not working / Gemini error**
- Check `GOOGLE_API_KEY` is set in `.env`
- The app works without it; only explanations fall back to rule-based text

**Port 5000 in use**
```bash
python backend/app.py --port 5001
# or
flask run --port 5001
```

**SQLite locked (concurrent writes)**
- Restart the Flask server
- In production, use PostgreSQL (configured via `DATABASE_URL`)

---

**Last Updated:** April 2026  
**Status:** All 6 phases complete — system is production-ready
