# Roommate Matching System - Project Structure

```
roommate-matching-system/
│
├── README.md                          # Project overview & setup
├── ARCHITECTURE.md                    # System architecture & design
├── SRS.md                            # Software Requirements Spec
├── requirements.txt                  # Python dependencies
├── docker-compose.yml                # Local development setup
├── .env.example                      # Environment variables template
├── .gitignore                        # Git ignore file
│
├── backend/                          # Python Flask Backend
│   ├── app.py                       # Main Flask application
│   ├── config.py                    # Configuration management
│   ├── requirements.txt             # Backend dependencies
│   │
│   ├── agents/                      # Multi-Agent System
│   │   ├── __init__.py
│   │   ├── base_agent.py            # Abstract agent base class
│   │   ├── user_profiling_agent.py  # Agent 1: User input validation
│   │   ├── preference_analysis_agent.py  # Agent 2: Vectorization
│   │   ├── compatibility_scoring_agent.py # Agent 3: Scoring
│   │   ├── room_matching_agent.py   # Agent 4: Room filtering
│   │   ├── conflict_detection_agent.py # Agent 5: Conflict analysis
│   │   ├── recommendation_engine_agent.py # Agent 6: Ranking & explanations
│   │   └── agent_orchestrator.py    # Controls agent flow
│   │
│   ├── models/                      # Database ORM models
│   │   ├── __init__.py
│   │   ├── user.py                  # User model
│   │   ├── preference.py            # Preference model
│   │   ├── room.py                  # Room model
│   │   ├── score.py                 # Compatibility score model
│   │   ├── match.py                 # Match recommendation model
│   │   └── conflict.py              # Conflict log model
│   │
│   ├── routes/                      # API endpoints
│   │   ├── __init__.py
│   │   ├── auth.py                  # Authentication routes
│   │   ├── users.py                 # User CRUD routes
│   │   ├── preferences.py           # Preference routes
│   │   ├── rooms.py                 # Room listing routes
│   │   ├── matching.py              # Matching engine routes
│   │   └── recommendations.py       # Recommendation routes
│   │
│   ├── utils/                       # Helper utilities
│   │   ├── __init__.py
│   │   ├── database.py              # Database connection
│   │   ├── validators.py            # Input validation
│   │   ├── jwt_handler.py           # JWT token management
│   │   ├── similarity_metrics.py    # Cosine similarity, etc.
│   │   └── error_handlers.py        # Custom error responses
│   │
│   ├── migrations/                  # Database migrations
│   │   ├── versions/
│   │   └── env.py
│   │
│   └── tests/                       # Backend unit tests
│       ├── __init__.py
│       ├── test_agents.py
│       ├── test_scoring.py
│       ├── test_user_management.py
│       └── test_routes.py
│
├── frontend/                        # Frontend (HTML/CSS/JS)
│   ├── index.html                  # Home page
│   ├── register.html               # Registration page
│   ├── login.html                  # Login page
│   ├── dashboard.html              # Main user dashboard
│   ├── preferences.html            # Preference setup form
│   ├── matches.html                # Matches/recommendations page
│   ├── rooms.html                  # Room listing page
│   ├── room-detail.html            # Single room detail page
│   ├── profile.html                # User profile page
│   ├── admin.html                  # Admin dashboard (optional)
│   │
│   ├── css/
│   │   ├── style.css               # Main stylesheet
│   │   ├── responsive.css          # Mobile responsive
│   │   └── theme.css               # Color scheme & themes
│   │
│   ├── js/
│   │   ├── main.js                 # Main JavaScript bundle
│   │   ├── auth.js                 # Authentication logic
│   │   ├── api.js                  # API client (fetch wrapper)
│   │   ├── preferences.js          # Preference form logic
│   │   ├── matches.js              # Matches page logic
│   │   ├── rooms.js                # Room filtering logic
│   │   └── utils.js                # Utility functions
│   │
│   ├── images/
│   │   ├── logo.png
│   │   └── placeholders/
│   │
│   └── fonts/
│       └── (web fonts if needed)
│
├── database/                        # Database files & schemas
│   ├── schema.sql                  # Complete database schema
│   ├── seed_data.sql               # Sample test data
│   ├── roommate_system.db          # SQLite database (dev)
│   └── migrations/                 # Migration scripts
│
├── docs/                           # Documentation
│   ├── API_DOCUMENTATION.md        # Complete API spec
│   ├── AGENT_GUIDE.md              # How agents work
│   ├── SETUP_GUIDE.md              # Installation & run instructions
│   ├── TESTING_GUIDE.md            # Test execution guide
│   ├── DEPLOYMENT_GUIDE.md         # Production deployment
│   └── examples/
│       ├── sample_requests.json    # Example API calls
│       └── sample_responses.json   # Example responses
│
├── deployment/                     # Deployment artifacts
│   ├── Dockerfile                  # Docker image definition
│   ├── docker-compose.yml          # Container orchestration
│   ├── nginx.conf                  # Web server config (production)
│   └── systemd/                    # Systemd service files
│
└── CHANGELOG.md                    # Version history
```

## Directory Descriptions

### `/backend` - Python Flask Backend
Contains all server-side logic:
- **agents/**: The 6 AI agents (main logic)
- **models/**: Database table definitions (SQLAlchemy)
- **routes/**: REST API endpoints
- **utils/**: Helper functions (DB, validation, JWT, etc.)
- **tests/**: Unit tests for each component

### `/frontend` - HTML/CSS/JavaScript
Client-side application:
- **HTML pages**: Each major page (register, dashboard, matches, rooms, etc.)
- **CSS**: Styling and responsive design
- **JS**: Client-side logic, API calls, event handling

### `/database`
Database-related files:
- **schema.sql**: CREATE TABLE statements
- **seed_data.sql**: Test data for development
- **.db file**: Actual SQLite database (git-ignored)

### `/docs`
Comprehensive documentation:
- API reference
- Agent behavior explanation
- Setup & deployment guides
- Testing procedures

### `/deployment`
Production-ready configurations:
- Docker setup
- Web server config
- Deployment scripts

---

## File Organization Rationale

**Why Agents in Separate Files?**
- Each agent is independent and can be tested in isolation
- Easy to extend/modify agent behavior
- Clear separation of concerns
- Matches multi-agent requirement

**Why Routes in Separate Files?**
- RESTful organization by resource type
- Easier to navigate and maintain
- Scalable as endpoints grow

**Why Utils Separate?**
- Shared logic across routes/agents
- Reusable components (similarity metrics, validators)
- Easier to mock for testing

**Why Tests Organized This Way?**
- Mirrors source code structure
- Easy to find tests for specific components
- CI/CD can run tests in parallel

---

## Key Files to Understand First

1. **ARCHITECTURE.md** - System design overview
2. **SRS.md** - Requirements & functional specs
3. **backend/app.py** - Flask app initialization
4. **backend/agents/agent_orchestrator.py** - Agent workflow
5. **frontend/js/api.js** - Frontend-backend communication
6. **docs/API_DOCUMENTATION.md** - Complete API reference

---

## Database File Location
- **Development**: `database/roommate_system.db` (SQLite, checked into git)
- **Production**: PostgreSQL (external, not in repo)

---

**Next Step**: Proceed with backend initialization and agent implementation
