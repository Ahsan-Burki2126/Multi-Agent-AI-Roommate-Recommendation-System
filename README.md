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
| **Room Listings** | 23+ real Pakistani room listings seeded across 8 cities (no external API needed) |
| **Post a Room** | Any user can post their own room listing |
| **Survey Data** | Pre-loaded with 327 real survey responses from IUB students |

---

## Quick Start

```bash
cd roommate-matching-system

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
copy .env.example .env       # Windows
cp .env.example .env         # Mac/Linux
# Set GOOGLE_API_KEY for Gemini AI (AI agents use this)

# Seed the database with Pakistani room listings
python seed_rooms.py

# Run migrations (adds new room fields if upgrading)
python migrate_db.py

# Start the server
python backend/app.py
# → http://localhost:5000
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

1. **`seed_rooms.py`** — 23 realistic Pakistani listings across Bahawalpur, Islamabad,
   Lahore, Karachi, Rawalpindi, Multan, Faisalabad, Peshawar.
   ```bash
   python seed_rooms.py           # add rooms
   python seed_rooms.py --clear   # wipe and reseed
   python seed_rooms.py --city Lahore   # seed one city only
   ```

2. **`POST /rooms`** — Any authenticated user can post their own room.

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
DATABASE_URL=sqlite:///./database/roommate_system.db
GOOGLE_API_KEY=AIza...        # Gemini AI (required for AI explanations)
FLASK_ENV=development
```

> `GOOGLE_API_KEY` is used **only for Gemini AI** agent explanations.
> Rooms, matching scores, and all other features work without it.

---

## Project Files

```
roommate-matching-system/
├── backend/
│   ├── app.py                    Flask factory
│   ├── config.py                 Dev / prod config
│   ├── agents/                   6 AI agents + orchestrator
│   ├── models/                   SQLAlchemy ORM models
│   ├── routes/                   REST API blueprints
│   └── services/                 (empty — no external services)
├── frontend/
│   ├── rooms.html                Room listing + AI matching UI
│   ├── matches.html              Roommate match results
│   ├── dashboard.html            User dashboard
│   ├── js/api.js                 API client (all endpoints)
│   └── css/                      Tailwind + custom styles
├── seed_rooms.py                 Seed 23 Pakistani room listings
├── migrate_db.py                 Add new Room columns to existing DB
├── seed_prod.py                  Seed 327 IUB survey users (production)
├── FYP_PROJECT_DOCUMENTATION.md  Full documentation for presentation
├── MODELS_QUICK_REFERENCE.md     Model API quick reference
└── PROJECT_STATUS_FINAL.md       Completion status per phase
```

---

## For FYP Examiners

**Run the app:**
```bash
python backend/app.py
# Open http://localhost:5000
```

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
