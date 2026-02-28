# Database Models Quick Reference

Quick lookup guide for developers implementing Phase 3 (Routes) and Phase 4 (Agents).

## Model Import

```python
from backend.models import (
    User, UserPreference, PreferenceVector,
    Room, CompatibilityScore, Recommendation, 
    ConflictLog, AuditLog
)
```

---

## User Model

### Creating a User
```python
user = User(
    email='alice@example.com',
    name='Alice Chen',
    phone='+1234567890',
    gender='female',
    dob=datetime(2000, 5, 15)
)
user.set_password('SecurePass123!')
db.session.add(user)
db.session.commit()
```

### Finding Users
```python
# By email
user = User.get_by_email('alice@example.com')

# By ID
user = User.get_by_id(123)

# Using query
users = User.query.filter_by(active=True).all()
```

### Authentication
```python
# Verify password
if user.check_password('SecurePass123!'):
    # Authentication successful
    pass
```

### Serialization
```python
# Public profile (no sensitive data)
user_dict = user.to_dict()  
# → {'email': '...', 'name': '...', 'gender': '...', ...}

# Full profile with relationships
profile = user.to_profile_dict()
```

### Validation
```python
is_valid, errors = user.validate()
if not is_valid:
    print(errors)  # ['Email is invalid', 'Password too short', ...]
```

---

## UserPreference Model

### Storing Preferences
```python
pref = UserPreference(
    user_id=user.user_id,
    budget_min=800,
    budget_max=1200,
    preferred_location='San Francisco',
    preferred_room_type='Shared',
    cleanliness_level='very_clean',
    schedule='night_owl',
    pets_ok=True,
    smoking_ok=False,
    noise_tolerance=7,
    age_min=22,
    age_max=30,
    lifestyle_keywords='tech, yoga, coffee'
)
db.session.add(pref)
db.session.commit()
```

### Querying
```python
# Get user's preference
pref = UserPreference.query.filter_by(user_id=user_id).first()

# Check if has vector
if pref.has_vector():
    vec = pref.preference_id  # or query PreferenceVector
```

### Validation
```python
is_valid, errors = pref.validate()
# Validates: budget_min < budget_max, age ranges, etc.
```

---

## PreferenceVector Model

### Creating Vectors (Analysis Agent)
```python
import numpy as np

# Convert preferences to vector
vector_data = [0.8, 0.7, 0.9, 0.6, 0.5]  # 5-dim example
vector_norm = np.linalg.norm(vector_data)

vec = PreferenceVector(
    user_id=user.user_id,
    vector_data=vector_data,
    vector_norm=vector_norm,
    preference_weights={
        'cosine_similarity': 0.3,
        'lifestyle': 0.2,
        'schedule': 0.2,
        'budget': 0.15,
        'habits': 0.15
    }
)
db.session.add(vec)
db.session.commit()
```

### Computing Similarity (Scoring Agent)
```python
vec1 = PreferenceVector.query.filter_by(user_id=user1_id).first()
vec2 = PreferenceVector.query.filter_by(user_id=user2_id).first()

# Cosine similarity
similarity = vec1.get_similarity_with(vec2)  # Returns 0-1

# Check if stale (> 30 days)
if vec1.is_stale(days=30):
    # Recompute vector
    pass
```

---

## Room Model

### Creating a Room Listing
```python
room = Room(
    owner_id=owner_user.user_id,
    title='Cozy Shared Room in Mission',
    description='Bright shared room with large window',
    location='San Francisco',
    address='123 Mission St, SF, CA 94103',
    room_type='Shared',  # or 'Single' or 'Master'
    rent_price=950,
    available_from=datetime.now(),
    amenities=['WiFi', 'AC', 'Washing Machine'],
    images=['room1.jpg', 'room2.jpg'],
    pets_allowed=True,
    smoking_allowed=False,
    is_available=True
)
db.session.add(room)
db.session.commit()
```

### Matching Against Preferences (Room Matching Agent)
```python
pref = user.preferences[0]  # or fetch from DB

# Check hard constraints
matches, reasons = room.matches_constraints(pref)
if not matches:
    print(f"Blocked: {reasons}")  # ['Pets not allowed', ...]
    continue

# Check soft matching
score = room.get_compatibility_score(pref)
# Returns 0-100, considering:
# - 40 points for budget match
# - 30 points for location match
# - 20 points for room type match
# - 10 points for amenities
```

### Quick Checks
```python
# Budget compatibility
room.matches_budget(budget_min, budget_max)  # bool

# Location
room.matches_location('san francisco')  # bool, case-insensitive

# Room type
room.matches_room_type('Shared')  # bool

# Has amenity
room.has_amenity('WiFi')  # bool
```

### Querying
```python
# Available rooms in location
rooms = Room.query.filter_by(
    location='San Francisco',
    is_available=True
).all()

# By owner
user_rooms = Room.query.filter_by(owner_id=user_id).all()
```

---

## CompatibilityScore Model

### Creating Scores (Scoring Agent)
```python
score = CompatibilityScore(
    user_a_id=user1.user_id,
    user_b_id=user2.user_id,
    overall_score=75,  # 0-100
    cosine_similarity_score=0.82,  # 0-1
    lifestyle_score=72,  # 0-100
    schedule_score=65,  # 0-100
    budget_score=78,  # 0-100
    habits_score=70,  # 0-100
    last_computed=datetime.now()
)
db.session.add(score)
db.session.commit()
```

### Querying Scores
```python
# Get score (handles both directions A→B and B→A)
score = CompatibilityScore.get_score_for_pair(user_a_id, user_b_id)

# OR query directly
score = CompatibilityScore.query.filter(
    ((CompatibilityScore.user_a_id == user_a_id) & 
     (CompatibilityScore.user_b_id == user_b_id)) |
    ((CompatibilityScore.user_a_id == user_b_id) & 
     (CompatibilityScore.user_b_id == user_a_id))
).first()
```

### Analysis
```python
# Component breakdown
components = score.get_component_breakdown()
# → {'overall': 75, 'cosine': 0.82, 'lifestyle': 72, ...}

# Strength description
label = score.get_strength_description()  # "Very Good Match" (70-84)

# Best/worst components
best = score.get_strongest_component()  # 'cosine_similarity_score'
worst = score.get_weakest_component()  # 'schedule_score'

# Filtering
above_threshold = score.overall_score >= 70
is_strong = score.is_above_threshold(threshold=75)
```

### Caching
```python
# Check if stale (> 7 days)
if score.is_stale(days=7):
    # Recompute score
    db.session.delete(score)
    db.session.commit()
```

---

## Recommendation Model

### Creating Recommendations (Recommendation Engine Agent)
```python
rec = Recommendation(
    requester_id=user1_id,
    match_type='roommate',  # or 'room'
    match_id=user2_id,
    match_score=82,
    explanation='Excellent lifestyle match with similar interests',
    conflict_warnings=[]  # or ['Schedule mismatch'] if soft conflicts
)
db.session.add(rec)
db.session.commit()
```

### Tracking Interactions
```python
# User viewed recommendation
rec.mark_viewed()
rec.view_date  # now set to datetime.now()

# User liked it
rec.mark_liked()
rec.liked = True

# User disliked it
rec.mark_disliked()
rec.liked = False
```

### Querying Recommendations
```python
# All for a user
recs = Recommendation.get_user_recommendations(user_id)

# Only unviewed
new_recs = Recommendation.get_new_recommendations(user_id, limit=10)

# Only liked
liked = Recommendation.query.filter_by(requester_id=user_id, liked=True).all()

# Get status
status = rec.get_interaction_status()  # 'new', 'viewed', 'liked', 'disliked'

# Compatibility label
label = rec.get_compatibility_label()  # "Very Good Match"
```

### Statistics
```python
# How many pending?
count = Recommendation.count_pending(user_id)

# Like rate
rate = Recommendation.get_like_rate(user_id)  # 0.0-1.0

# Recent recs
recent = Recommendation.get_recent_recommendations(user_id, limit=5)
```

---

## ConflictLog Model

### Recording Conflicts (Conflict Detection Agent)

**Hard Conflict (Deal-breaker):**
```python
conflict = ConflictLog.create_hard_conflict(
    user_a_id=user_a_id,
    user_b_id=user_b_id,
    reason='Pet policy mismatch',
    details='User A requires pets allowed, User B forbids pets'
)
# severity auto-set to 9
```

**Soft Conflict (Warning):**
```python
conflict = ConflictLog.create_soft_conflict(
    user_a_id=user_a_id,
    user_b_id=user_b_id,
    reason='Schedule mismatch',
    details='User A: early bird (6am), User B: night owl (2am)',
    severity=4
)
```

### Querying Conflicts

**Before recommending:**
```python
# Check for hard blockers
has_hard = ConflictLog.has_hard_conflicts(user_a_id, user_b_id)
if has_hard:
    # Don't recommend
    continue

# OR get all conflicts
conflicts = ConflictLog.get_conflicts_for_pair(user_a_id, user_b_id)
for conflict in conflicts:
    if conflict.is_hard_conflict():
        break  # Hard blocker
```

**Get specific type:**
```python
hard_only = ConflictLog.get_hard_conflicts_for_pair(user_a_id, user_b_id)
soft_only = ConflictLog.get_soft_conflicts_for_pair(user_a_id, user_b_id)
```

### Analysis
```python
# Check type
if conflict.is_hard_conflict():
    # Deal-breaker
    pass
elif conflict.is_soft_conflict():
    # Warning
    pass

# Severity label
label = conflict.get_severity_label()
# 1='Minor', 3='Low', 5='Medium', 7='High', 9='Critical'
```

---

## AuditLog Model

### Recording Decisions (All Agents)
```python
import json

AuditLog(
    agent_name='Profiling Agent',
    action='user_registered',
    entity_type='user',
    entity_id=user.user_id,
    details=json.dumps({
        'email': user.email,
        'verified': True,
        'active': True
    }),
    timestamp=datetime.now()
)
```

### Querying Audit Trail

**Trace an entity (e.g., user #123):**
```python
logs = AuditLog.get_logs_for_entity('user', 123)
# Shows: created, preferences set, vectors computed, 
#        scores generated, recommendations made, interactions tracked

for log in logs:
    print(f"{log.timestamp} | {log.agent_name}: {log.action}")
```

**Trace a recommendation decision:**
```python
trace = AuditLog.get_recommendation_trace(user_a_id, user_b_id)
# Shows complete pipeline: Profiling → Analysis → Scoring → 
#        Conflict Detection → Recommendation Engine
```

**Agent activity:**
```python
# How many decisions did Scoring Agent make?
count = AuditLog.count_logs(agent_name='Scoring Agent')

# How active in last 24 hours?
recent = AuditLog.get_agent_activity('Profiling Agent', hours=24)

# Last 100 decisions from all agents
timeline = AuditLog.get_agent_timeline(limit=100)
```

---

## Common Patterns

### Pattern 1: User Registration & Profile Setup
```python
# Step 1: Create user (Profiling Agent)
user = User(email=email, name=name, phone=phone, gender=gender)
user.set_password(password)
db.session.add(user)
db.session.commit()

# Step 2: Record in audit
AuditLog(
    agent_name='Profiling Agent',
    action='user_registered',
    entity_type='user',
    entity_id=user.user_id,
    details=json.dumps({'email': email, 'verified': False})
)

# Step 3: Create preferences (Preference Agent)
pref = UserPreference(user_id=user.user_id, ...)
db.session.add(pref)
db.session.commit()

# Step 4: Vectorize (Analysis Agent)
vec = PreferenceVector(user_id=user.user_id, ...)
db.session.add(vec)
db.session.commit()
```

### Pattern 2: Finding Good Matches
```python
# Step 1: Get user's vector
requester = User.get_by_id(requester_id)
requester_vec = PreferenceVector.query.filter_by(
    user_id=requester_id
).first()

# Step 2: Find similar users
all_users = User.query.filter(User.user_id != requester_id).all()
for candidate in all_users:
    candidate_vec = PreferenceVector.query.filter_by(
        user_id=candidate.user_id
    ).first()
    
    if not candidate_vec:
        continue
    
    # Step 3: Compute score (Scoring Agent)
    sim_score = requester_vec.get_similarity_with(candidate_vec)
    
    # Step 4: Check for conflicts (Conflict Detection Agent)
    if ConflictLog.has_hard_conflicts(requester_id, candidate.user_id):
        continue  # Skip this match
    
    # Step 5: Create recommendation (Recommendation Engine)
    score = CompatibilityScore(
        user_a_id=requester_id,
        user_b_id=candidate.user_id,
        overall_score=int(sim_score * 100),
        ...
    )
    db.session.add(score)
    
    rec = Recommendation(
        requester_id=requester_id,
        match_type='roommate',
        match_id=candidate.user_id,
        match_score=int(sim_score * 100),
        explanation=f"Good match based on preferences"
    )
    db.session.add(rec)

db.session.commit()
```

### Pattern 3: Room Search
```python
# Get user preferences
user = User.get_by_id(user_id)
pref = user.preferences[0]

# Search rooms
rooms = Room.query.filter_by(location='San Francisco').all()

# Score each room
for room in rooms:
    # Hard constraint check
    matches, _ = room.matches_constraints(pref)
    if not matches:
        continue
    
    # Soft score
    score = room.get_compatibility_score(pref)
    
    if score >= 70:
        # Recommend
        rec = Recommendation(
            requester_id=user_id,
            match_type='room',
            match_id=room.room_id,
            match_score=score,
            explanation=f"Good room match: {score}/100"
        )
        db.session.add(rec)

db.session.commit()
```

---

## Validation Checklist

Before committing to database:

```python
# User
user = User(...)
is_valid, errors = user.validate()
if not is_valid:
    return bad_request(errors)

# Preference
pref = UserPreference(...)
is_valid, errors = pref.validate()
if not is_valid:
    return bad_request(errors)

# Room
room = Room(...)
is_valid, errors = room.validate()
if not is_valid:
    return bad_request(errors)
```

---

## Performance Tips

1. **Use indexes**: Email, location, user_id are indexed
2. **Batch operations**: Use `db.session.add_all()` instead of add()
3. **Lazy loading**: Be careful with relationships, use eager loading if needed
4. **Check staleness**: Before using scores/vectors, check `is_stale()`
5. **Connection pooling**: SQLAlchemy handles this automatically
6. **Query filtering**: Do filtering in database, not in Python

```python
# Good - database filters
rooms = Room.query.filter_by(location='SF', is_available=True).all()

# Bad - Python filters
all_rooms = Room.query.all()
sf_rooms = [r for r in all_rooms if r.location == 'SF']
```

