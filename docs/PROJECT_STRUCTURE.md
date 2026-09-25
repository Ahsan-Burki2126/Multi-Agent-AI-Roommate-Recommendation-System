# Project Structure

Multi-Agent AI Roommate Recommendation System — final year project, The Islamia
University of Bahawalpur.

## The short version

Three independent pieces:

1. **`backend/`** — a Flask REST API on port 5000. All the Python lives here.
2. **`frontend/`** — plain HTML/CSS/JS served as static files on port 8000.
   No build step, no npm, no framework.
3. **A SQLite file** at `backend/database/roommate_system.db` — the database.

The frontend talks to the backend over HTTP only; `frontend/js/api.js` sets the
base URL. They are separate programs, which is why you start two servers.

```
Browser  ──HTTP──▶  backend/routes/  ──▶  backend/agents/  ──▶  backend/models/  ──▶  SQLite
```

## Tree

```
FYP/
├── README.md                  Overview and quickstart
├── requirements.txt           Python dependencies
├── pytest.ini                 Limits pytest to backend/tests
├── vercel.json                Deployment routing (points at backend/api/index.py)
├── .env.example               Template for .env (never commit the real one)
│
├── backend/                   ── Flask API ──────────────────────────────
│   ├── app.py                 Entry point. create_app() wires everything up.
│   │                          Run with: python -m backend.app
│   ├── config.py              Development / testing / production settings,
│   │                          including which database each one uses
│   ├── database.py            The SQLAlchemy `db` object, kept in its own
│   │                          module so models and app can both import it
│   │                          without a circular import
│   ├── init_db.py             Creates the tables (db.create_all())
│   │
│   ├── models/                One file per table
│   │   ├── user.py            users
│   │   ├── preference.py      user_preferences + preference_vectors
│   │   ├── room.py            rooms
│   │   ├── score.py           compatibility_scores
│   │   ├── match.py           recommendations
│   │   ├── conflict.py        conflict_log
│   │   └── audit.py           audit_log
│   │
│   ├── routes/                HTTP endpoints, one blueprint per resource
│   │   ├── auth.py            /auth      register, login, verify, password
│   │   ├── users.py           /users     profile read/update, search
│   │   ├── preferences.py     /preferences
│   │   ├── rooms.py           /rooms     list, search, create, /rooms/matched
│   │   ├── matching.py        /matches   compatibility scores, conflicts
│   │   ├── recommendations.py /recommendations  like / pass / stats
│   │   └── orchestrate.py     /orchestrate  runs the agent pipelines
│   │
│   ├── agents/                ── The multi-agent system ──
│   │   ├── base_agent.py                  Shared base class + AgentResult
│   │   ├── user_profiling_agent.py        1. validate the user
│   │   ├── preference_analysis_agent.py   2. turn preferences into vectors
│   │   ├── compatibility_scoring_agent.py 3. score user pairs
│   │   ├── room_matching_agent.py         4. filter and rank rooms
│   │   ├── conflict_detection_agent.py    5. find deal-breakers
│   │   ├── recommendation_engine_agent.py 6. rank and explain
│   │   └── agent_orchestrator.py          runs them in sequence
│   │
│   ├── api/index.py           Serverless wrapper — only used on Vercel
│   ├── database/              Holds the live roommate_system.db
│   └── tests/                 pytest suite (test_models.py)
│
├── frontend/                  ── Static site, no build step ─────────────
│   ├── index.html             Public landing page
│   ├── login.html             Public
│   ├── register.html          Public
│   ├── dashboard.html         ─┐
│   ├── matches.html            │
│   ├── rooms.html              ├─ require a login
│   ├── preferences.html        │
│   ├── profile.html            │
│   ├── settings.html           │
│   ├── ai-agents.html         ─┘ pipeline status and agent log
│   │
│   ├── css/
│   │   ├── design-system.css  Theme tokens — edit colours HERE
│   │   └── style.css          Shared component styles
│   ├── js/
│   │   ├── api.js             Every backend call goes through this
│   │   └── auth.js            Login state and token handling
│   └── images/rooms/          room-01..10.svg — listing artwork
│
├── scripts/                   One-off utilities — see scripts/README.md
├── data/                      survey_user_credentials.xlsx (source survey)
└── docs/                      This file and the written report
```

## Where to change things

| To change… | Edit |
|---|---|
| Theme colours | `frontend/css/design-system.css` |
| What an API endpoint returns | the matching file in `backend/routes/` |
| How matching decides a score | the relevant file in `backend/agents/` |
| A database column | the model in `backend/models/`, then migrate |
| Which database is used | `backend/config.py` |
| Room demo data | `scripts/seed_rooms_for_matching.py` |

## Two things that trip people up

**The survey's `city` field holds an area category, not a city.** Values are
`Near University/College Area`, `Residential Area`, `Downtown/City Center`,
`Near Workplace/Office District`, `Suburban Area`. Room `location` is stored as
`"<locality>, <area category>"` so that the area category is still a substring —
that is what the Room Matching Agent filters on. A room whose location is just a
city name will never match a survey respondent.

**`roommate-matching-system/`** — if you see this folder on disk, it is a second
full copy of this project with its own git history. It is in `.gitignore` and is
not part of the project. Work pushed from it once left the GitHub branch ahead of
the main working copy, so always `git fetch` and check before pushing.
