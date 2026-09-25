# AI-Powered Roommate Matching System

A full-stack web application that uses a **6-agent AI pipeline** to match people looking for roommates and rooms — built as a Final Year Project (FYP).

---

## What It Does

| Feature | Description |
|---|---|
| **Roommate Matching** | Compatibility scores between users based on budget, lifestyle, schedule, habits |
| **Room Matching** | Rooms scored against your preferences and ranked by fit percentage |
| **AI Explanations** | Google Gemini generates natural-language explanations for every match |
| **Conflict Detection** | Identifies deal-breakers (pets, smoking, budget mismatch) before they happen |
| **Room Listings** | 237 listings — 24 hand-written Pakistani hostels plus survey-aligned stock the matcher can rank (no external API needed) |
| **Post a Room** | Any user can post their own room listing |
| **Survey Data** | Pre-loaded with 319 real survey responses from IUB students |

---

## Quick Start

The app is two servers: a Flask API and a static frontend. You need both.

```bash
# 1. Dependencies
pip install -r requirements.txt

# 2. Environment
copy .env.example .env       # Windows
cp .env.example .env         # macOS / Linux
# then set GOOGLE_API_KEY in .env — the AI agents use Gemini
```

**Terminal 1 — backend (port 5000):**

```bash
python -m backend.app
```

**Terminal 2 — frontend (port 8000):**

```bash
cd frontend
python -m http.server 8000
```

Open <http://localhost:8000>. The database ships with data already loaded, so
there is nothing to seed for a normal run.

Log in with any survey account — e.g. `abdul.ahad.0002@survey.iub.edu.pk`,
password `Survey@2024`.

### Starting from an empty database

```bash
python backend/init_db.py                      # create the tables
python scripts/load_survey_data.py             # import the survey respondents
python scripts/seed_rooms_for_matching.py      # rooms the AI can actually match
```

### Running the tests

```bash
pytest
```

---

## Architecture

```
Frontend (HTML/CSS/JS)
    ↓  REST / JSON
Flask Backend (port 5000)
    ↓
Agent Orchestrator
    ├── User Profiling Agent       validates user profile
    ├── Preference Analysis Agent  converts prefs → numerical vectors
    ├── Compatibility Scoring Agent  cosine similarity + sub-scores
    ├── Room Matching Agent        filters & scores rooms
    ├── Conflict Detection Agent   flags hard/soft blockers
    └── Recommendation Engine      ranks results + Gemini explanations
    ↓
SQLite (dev) / PostgreSQL / Neon (prod)
```

---

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | HTML5 + Tailwind CSS (CDN) + Vanilla JS |
| Backend | Python 3 + Flask + Flask-JWT-Extended |
| AI Agents | LangChain + Google Gemini (`gemini-2.0-flash`) |
| Similarity | NumPy (cosine similarity on preference vectors) |
| Database | SQLite (dev) / PostgreSQL via pg8000 (prod) |
| Deployment | Vercel (frontend + serverless backend) |

---

## Key API Endpoints

### Authentication
```
POST /auth/register       Create account
POST /auth/login          Login → JWT token
GET  /auth/verify         Verify token
```

### Rooms
```
GET  /rooms               List all available rooms (paginated)
GET  /rooms/matched       Rooms scored against current user's preferences
POST /rooms               Post a new room listing
GET  /rooms/<id>          Room detail (includes owner phone)
PUT  /rooms/<id>          Update room (owner only)
DELETE /rooms/<id>        Remove listing (owner only)
GET  /rooms/search        Filter by location / price / type
GET  /rooms/user/<id>     Rooms posted by a user
```

### Matching Pipeline
```
POST /orchestrate/matches    Full 6-agent roommate matching pipeline
POST /orchestrate/rooms      Room matching pipeline with AI summary
GET  /orchestrate/status     Agent system health
```

### Matches
```
GET  /matches/user/<id>      Computed compatibility scores
POST /matches/compute        Trigger scoring for current user
GET  /matches/conflicts/<a>/<b>   Conflict check between two users
```

---

## Room System

Rooms work without any external API. Data comes from:

1. **`scripts/seed_rooms_by_city.py`** — 24 realistic Pakistani listings across
   Bahawalpur, Islamabad, Lahore, Karachi, Rawalpindi, Multan, Faisalabad, Peshawar.
   ```bash
   python scripts/seed_rooms_by_city.py           # add rooms
   python scripts/seed_rooms_by_city.py --clear   # wipe and reseed
   python scripts/seed_rooms_by_city.py --city Lahore   # seed one city only
   ```

2. **`scripts/seed_rooms_for_matching.py`** — survey-aligned stock so every
   respondent gets matches. This is what makes AI room matching return results.

3. **`POST /rooms`** — Any authenticated user can post their own room.

### Room Compatibility Score
`GET /rooms/matched` returns every available room pre-scored against the
current user's preferences. Score = 0–100 based on:
- Budget overlap (40 pts)
- Location match (30 pts)
- Room type preference (20 pts)
- Amenity coverage (10 pts)

---

## Database Schema

```
users                    user accounts
user_preferences         budget, location, lifestyle prefs
preference_vectors       vectorised prefs for cosine similarity
rooms                    room listings
  ├─ location            city name
  ├─ address             full street address
  ├─ latitude/longitude  map coordinates (nullable)
  ├─ place_id            Google Place ID (nullable, for future use)
  ├─ google_rating       star rating (nullable)
  └─ google_maps_url     direct maps link (nullable)
compatibility_scores     cached pair-wise match scores
conflict_log             detected hard/soft conflicts
recommendations          ranked match list shown to users
audit_log                every agent decision, timestamped
```

---

## Environment Variables (`.env`)

```
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
DATABASE_URL=sqlite:///./backend/database/roommate_system.db
GOOGLE_API_KEY=AIza...        # Gemini AI (required for AI explanations)
FLASK_ENV=development
```

> `GOOGLE_API_KEY` is used **only for Gemini AI** agent explanations.
> Rooms, matching scores, and all other features work without it.

---

## Project Files

```
FYP/
├── backend/          Flask API — app.py, config.py, models/, routes/, agents/
│                     plus database/ (the live SQLite file) and tests/
├── frontend/         Static HTML/CSS/JS — no build step
│                     css/design-system.css holds the theme tokens
├── scripts/          Seeders and one-off utilities — see scripts/README.md
├── data/             survey_user_credentials.xlsx (the source survey)
└── docs/             Written report, schema reference, structure guide
```

**[docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) has the full annotated
tree** — what every folder is for, and where to change things.

Other documentation:

| File | Contents |
|---|---|
| [docs/FYP_PROJECT_DOCUMENTATION.md](docs/FYP_PROJECT_DOCUMENTATION.md) | Full write-up for presentation |
| [docs/MODELS_QUICK_REFERENCE.md](docs/MODELS_QUICK_REFERENCE.md) | Model API quick reference |
| [docs/PROJECT_STATUS_FINAL.md](docs/PROJECT_STATUS_FINAL.md) | Completion status per phase |
| [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) | Longer setup walkthrough |
| [docs/schema.sql](docs/schema.sql) | SQL schema reference |
| [scripts/README.md](scripts/README.md) | What each script does |

---

## For FYP Examiners

**Run the app** (two terminals):
```bash
python -m backend.app              # API on :5000
cd frontend && python -m http.server 8000   # UI on :8000
# Open http://localhost:8000
```
Log in as `abdul.ahad.0002@survey.iub.edu.pk` / `Survey@2024`.

**Test user flow:**
1. Register → complete preferences form
2. Dashboard → trigger AI roommate matching
3. Rooms → browse rooms with compatibility scores
4. Click "Find My Best Rooms (AI)" → AI ranks rooms by fit
5. Click Contact → see owner phone number

**Key code to review:**
- `backend/agents/agent_orchestrator.py` — pipeline controller
- `backend/agents/compatibility_scoring_agent.py` — scoring math
- `backend/routes/rooms.py` — room endpoints incl. `/matched`
- `backend/models/room.py` — Room ORM model with scoring method

---

**Last Updated:** April 2026
