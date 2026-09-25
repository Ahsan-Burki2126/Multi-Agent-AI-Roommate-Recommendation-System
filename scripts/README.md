# Scripts

One-off utilities. Run them from the project root with the virtualenv Python:

```bash
.venv/Scripts/python.exe scripts/<name>.py
```

Each script adds the project root to `sys.path` itself, so it does not matter
which directory you are standing in.

## Loading data

| Script | What it does |
|---|---|
| `load_survey_data.py` | Imports the student survey (`data/survey_user_credentials.xlsx`) into `users` and `user_preferences`. This is where the 319 survey accounts come from. Default password for every imported account is `Survey@2024`. |
| `create_test_accounts.py` | Creates hand-made demo accounts for manual testing. |
| `seed_prod.py` | Production seed: sets up landlord accounts and their listings against `DATABASE_URL`. |

## Seeding rooms

There are two room seeders because they do different jobs — keep both.

| Script | What it does |
|---|---|
| `seed_rooms_by_city.py` | ~24 hand-written, realistic Pakistani hostel listings keyed to real cities (Bahawalpur, Lahore, Karachi…). Good for a believable demo, but the locations are plain city names, so the AI matcher will not match them to survey respondents. |
| `seed_rooms_for_matching.py` | ~213 generated listings derived from the survey's own distributions. Locations embed the five survey area categories, prices sit inside the real budget bands, and a coverage pass guarantees every respondent gets at least 5 matches. **This is the one that makes room matching work.** |

```bash
# add survey-aligned rooms on top of whatever is already there
.venv/Scripts/python.exe scripts/seed_rooms_for_matching.py

# start over with exactly 180
.venv/Scripts/python.exe scripts/seed_rooms_for_matching.py --reset --count 180 --seed 42
```

## Database maintenance

| Script | What it does |
|---|---|
| `migrate_db.py` | Applies schema changes to an existing database. |
| `reset_and_test.py` | Drops and rebuilds the database, then runs a quick check. **Destructive.** |
| `check_conflicts.py` | Prints rows from the conflict log. |

## Checks

`run_tests.py` is a wrapper that runs the suite plus some extra checks.
The real unit tests live in `backend/tests/` and run with `pytest` from the
project root.

The `smoke_*.py` scripts hit a **running** server (start the backend first) and
print what they find. They are not pytest tests — they were named `test_*.py`
once, which made `pytest` try to import them and fail during collection.

| Script | Needs a running backend? |
|---|---|
| `smoke_agents.py` | no — exercises the agent classes directly |
| `smoke_langchain.py` | no — checks LangChain imports and app creation |
| `smoke_llm.py` | no — checks the Gemini key works |
| `smoke_pipeline.py` | **yes** — calls `POST /orchestrate/matches` over HTTP |
