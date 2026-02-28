# Development Roadmap
## Complete Implementation Path for Roommate Matching System

---

## 📋 Overview

This roadmap maps the exact sequence of implementation from current state to production-ready system. Each section includes:
- **What to build** - Specific files/components
- **Why it matters** - Business/technical justification  
- **How to test** - Validation approach
- **Acceptance criteria** - Success metrics
- **Estimated time** - Rough duration

---

## 🎯 Current Status: Foundation Phase ✅ COMPLETE

**What's Done:**
- ✅ Architecture & design documented
- ✅ Database schema created
- ✅ Flask app skeleton
- ✅ Base agent class
- ✅ Configuration system

**We're Here 👇**
```
Phase 1: Foundation ✅
Phase 2: Models (DATABASE LAYER)
Phase 3: Routes (API LAYER)
Phase 4: Agents (AI LAYER)
Phase 5: Frontend (UI LAYER)
Phase 6: Testing & Deployment
```

---

## 📦 PHASE 2: Database Models (Est. 1-2 Days)

### Objective
Create SQLAlchemy ORM models that map to database tables. Models are the bridge between Python code and database.

### Files to Create

#### 1. `backend/models/user.py`
**Purpose:** User account model

**What to include:**
```python
class User(db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column(Integer, primary_key=True)
    email = db.Column(String(255), unique=True, nullable=False)
    password_hash = db.Column(String(255), nullable=False)
    full_name = db.Column(String(255), nullable=False)
    gender = db.Column(Enum('M', 'F', 'Other'))
    city = db.Column(String(100))
    phone = db.Column(String(20))
    profile_picture = db.Column(String(500))
    bio = db.Column(Text)
    is_active = db.Column(Boolean, default=True)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    preferences = db.relationship('UserPreference', back_populates='user')
    rooms = db.relationship('Room', back_populates='owner')
    
    def set_password(self, password):
        """Hash and set password"""
        
    def check_password(self, password):
        """Verify password"""
```

**Key Methods:**
- `set_password(password)` - Hash password with bcrypt
- `check_password(password)` - Verify password
- `to_dict()` - Convert to JSON-serializable dict
- `get_by_email(email)` - Lookup user

**Tests:**
```python
def test_user_creation():
def test_password_hashing():
def test_user_relationships():
```

#### 2. `backend/models/preference.py`
**Purpose:** User preferences & vectorized preferences

```python
class UserPreference(db.Model):
    __tablename__ = 'user_preferences'
    
    preference_id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer, ForeignKey('users.user_id'), unique=True)
    
    # Budget
    budget_min = db.Column(Numeric(8,2), nullable=False)
    budget_max = db.Column(Numeric(8,2), nullable=False)
    
    # Location & Demographics
    preferred_location = db.Column(String(200))
    gender_preference = db.Column(Enum('M', 'F', 'Any'), default='Any')
    age_min = db.Column(Integer)
    age_max = db.Column(Integer)
    
    # Lifestyle
    cleanliness_level = db.Column(Enum('Very Clean', 'Clean', 'Average', 'Relaxed'))
    schedule = db.Column(Enum('9-5 Job', 'Night Shift', 'Student', 'Flexible'))
    smoking_ok = db.Column(Boolean, default=False)
    pets_ok = db.Column(Boolean, default=False)
    noise_tolerance = db.Column(Integer)
    
    # Room
    preferred_room_type = db.Column(Enum('Single', 'Shared', 'Any'))
    lease_duration_months = db.Column(Integer)
    
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', back_populates='preferences')
    vectors = db.relationship('PreferenceVector', back_populates='preference')

class PreferenceVector(db.Model):
    __tablename__ = 'preference_vectors'
    
    vector_id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer, ForeignKey('users.user_id'), unique=True)
    vector_data = db.Column(JSON)  # [0.5, 0.8, 0.3, ...]
    vector_norm = db.Column(Numeric(10,4))
    preference_weights = db.Column(JSON)
    computed_at = db.Column(DateTime, default=datetime.utcnow)
```

**Key Methods:**
- `to_dict()` - Convert to dict
- `validate()` - Check constraints (budget_min < budget_max, etc.)
- `get_vector()` - Return preference vector array
- `set_vector(vector_data)` - Store new vector

#### 3. `backend/models/room.py`
**Purpose:** Room listing model

```python
class Room(db.Model):
    __tablename__ = 'rooms'
    
    room_id = db.Column(Integer, primary_key=True)
    owner_id = db.Column(Integer, ForeignKey('users.user_id'), nullable=False)
    
    title = db.Column(String(255), nullable=False)
    description = db.Column(Text)
    location = db.Column(String(200), nullable=False)
    
    rent_price = db.Column(Numeric(8,2), nullable=False)
    room_type = db.Column(Enum('Single', 'Shared', 'Master'), nullable=False)
    bedrooms = db.Column(Integer)
    bathrooms = db.Column(Numeric(3,1))
    
    amenities = db.Column(JSON)  # ["WiFi", "AC", "Kitchen"]
    smoking_allowed = db.Column(Boolean, default=False)
    pets_allowed = db.Column(Boolean, default=False)
    images = db.Column(JSON)  # [url1, url2, ...]
    
    is_available = db.Column(Boolean, default=True)
    available_from = db.Column(Date)
    lease_duration_months = db.Column(Integer)
    
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    owner = db.relationship('User', back_populates='rooms')
```

**Key Methods:**
- `to_dict()` - JSON representation
- `matches_budget(budget_min, budget_max)` - Price compatibility
- `has_amenity(amenity)` - Check if room has feature
- `to_listing()` - Display format

#### 4. `backend/models/score.py`
**Purpose:** Compatibility scores

```python
class CompatibilityScore(db.Model):
    __tablename__ = 'compatibility_scores'
    
    score_id = db.Column(Integer, primary_key=True)
    user_a_id = db.Column(Integer, ForeignKey('users.user_id'), nullable=False)
    user_b_id = db.Column(Integer, ForeignKey('users.user_id'), nullable=False)
    
    overall_score = db.Column(Numeric(5,2), nullable=False)
    lifestyle_score = db.Column(Numeric(5,2))
    budget_score = db.Column(Numeric(5,2))
    schedule_score = db.Column(Numeric(5,2))
    habits_score = db.Column(Numeric(5,2))
    age_match_score = db.Column(Numeric(5,2))
    
    computed_at = db.Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('user_a_id', 'user_b_id'),
    )
```

**Key Methods:**
- `get_component_breakdown()` - Return all scores as dict
- `is_above_threshold(threshold)` - Score filtering
- `to_dict()` - JSON output

#### 5. `backend/models/match.py`
**Purpose:** Recommendations shown to users

```python
class Recommendation(db.Model):
    __tablename__ = 'recommendations'
    
    recommendation_id = db.Column(Integer, primary_key=True)
    requester_id = db.Column(Integer, ForeignKey('users.user_id'), nullable=False)
    match_type = db.Column(Enum('roommate', 'room'), nullable=False)
    match_id = db.Column(Integer, nullable=False)  # user_id or room_id
    
    match_score = db.Column(Numeric(5,2), nullable=False)
    explanation = db.Column(Text)
    conflict_warnings = db.Column(JSON)
    
    viewed_at = db.Column(DateTime)
    liked = db.Column(Boolean)  # True/False/None
    
    created_at = db.Column(DateTime, default=datetime.utcnow)
```

**Key Methods:**
- `mark_viewed()` - Set viewed_at
- `mark_liked()` - Set liked flag
- `get_explanation()` - Return explanation text

#### 6. `backend/models/conflict.py`
**Purpose:** Conflict detection results

```python
class ConflictLog(db.Model):
    __tablename__ = 'conflict_log'
    
    conflict_id = db.Column(Integer, primary_key=True)
    user_a_id = db.Column(Integer, ForeignKey('users.user_id'))
    user_b_id = db.Column(Integer, ForeignKey('users.user_id'))
    room_id = db.Column(Integer, ForeignKey('rooms.room_id'))
    
    conflict_type = db.Column(Enum('Hard', 'Soft'), nullable=False)
    description = db.Column(Text, nullable=False)
    severity = db.Column(Integer)  # 1-10
    
    auto_generated_at = db.Column(DateTime, default=datetime.utcnow)
```

#### 7. `backend/models/audit.py` (Optional)
**Purpose:** Audit logging for transparency

```python
class AuditLog(db.Model):
    __tablename__ = 'audit_log'
    
    log_id = db.Column(Integer, primary_key=True)
    agent_name = db.Column(String(100), nullable=False)
    action = db.Column(String(255), nullable=False)
    entity_type = db.Column(String(50))
    entity_id = db.Column(Integer)
    details = db.Column(Text)  # JSON
    timestamp = db.Column(DateTime, default=datetime.utcnow)
```

### Testing for Phase 2

Create `backend/tests/test_models.py`:
```python
def test_user_model():
    """Test user creation and password hashing"""

def test_preference_relationships():
    """Test user->preference relationship"""

def test_room_model():
    """Test room creation and constraints"""

def test_compatibility_score_model():
    """Test score model"""
```

### Success Criteria ✓
- [ ] All models import without errors
- [ ] Models defined in app.py
- [ ] Database tables create successfully
- [ ] Model tests pass
- [ ] Relationships work (can navigate from user → preferences)

### Estimate: 1-2 days

---

## 🔌 PHASE 3: API Routes (Est. 2-3 Days)

### Objective
Create Flask routes that handle HTTP requests and responses. Each route maps to a specific use case.

### Files to Create

#### 1. `backend/routes/auth.py` - Authentication
```python
@auth_bp.route('/register', methods=['POST'])
def register():
    """
    POST /auth/register
    Body: {email, password, full_name, gender}
    Returns: {user_id, email, message}
    """
    
@auth_bp.route('/login', methods=['POST'])
def login():
    """
    POST /auth/login
    Body: {email, password}
    Returns: {token, user_id, expires_in}
    """
    
@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    POST /auth/logout
    Header: Authorization: Bearer <token>
    Returns: {message}
    """
    
@auth_bp.route('/profile', methods=['GET'])
def profile():
    """
    GET /auth/profile
    Header: Authorization: Bearer <token>
    Returns: {user_id, email, full_name, ...}
    """
```

**Key Features:**
- Input validation (email format, password strength)
- User Profiling Agent call
- JWT token generation
- Error handling (duplicate email, weak password, etc.)

#### 2. `backend/routes/users.py` - User Management
```python
@users_bp.route('/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get user profile"""
    
@users_bp.route('/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """Update user info (city, bio, phone, etc.)"""
    
@users_bp.route('/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete user account"""
```

#### 3. `backend/routes/preferences.py` - Preferences
```python
@preferences_bp.route('', methods=['POST'])
def create_preferences():
    """
    POST /preferences
    Body: {budget_min, budget_max, preferred_location, ...}
    Uses: User Profiling Agent + Preference Analysis Agent
    Returns: {preference_id, vectors, weights}
    """
    
@preferences_bp.route('/<int:user_id>', methods=['GET'])
def get_preferences(user_id):
    """Get user preferences"""
    
@preferences_bp.route('/<int:pref_id>', methods=['PUT'])
def update_preferences(pref_id):
    """Update preferences (triggers re-vectorization)"""
```

#### 4. `backend/routes/rooms.py` - Room Management
```python
@rooms_bp.route('', methods=['POST'])
def create_room():
    """
    POST /rooms
    Body: {title, description, location, rent_price, room_type, ...}
    Returns: {room_id, ...}
    """
    
@rooms_bp.route('', methods=['GET'])
def list_rooms():
    """
    GET /rooms?location=NYC&price_min=400&price_max=800&room_type=Single
    Uses: Room Matching Agent for filtering
    Returns: [room1, room2, ...]
    """
    
@rooms_bp.route('/<int:room_id>', methods=['GET'])
def get_room(room_id):
    """Get room details"""
    
@rooms_bp.route('/<int:room_id>', methods=['PUT'])
def update_room(room_id):
    """Update room (owner only)"""
    
@rooms_bp.route('/<int:room_id>', methods=['DELETE'])
def delete_room(room_id):
    """Delete room (owner only)"""
```

#### 5. `backend/routes/matching.py` - Matching Engine
```python
@matching_bp.route('/roommates/<int:user_id>', methods=['GET'])
def find_roommates(user_id):
    """
    GET /matches/roommates/:user_id
    Uses: Orchestrator running ALL 6 agents
    Returns: [
        {
            match_id: 123,
            name: "Alice",
            score: 78.5,
            components: {lifestyle: 82, budget: 75, ...},
            explanation: "...",
            conflicts: ["soft: schedule mismatch"]
        },
        ...
    ]
    """
    # Call agent_orchestrator
    result = orchestrator.execute_pipeline([
        ('profiling_agent', {'user_id': user_id}),
        ('analysis_agent', {...}),
        ('scoring_agent', {...}),
        ('conflict_detection_agent', {...}),
        ('recommendation_engine', {...})
    ])
    return jsonify(result)
```

#### 6. `backend/routes/recommendations.py`
```python
@recommendations_bp.route('/<int:user_id>', methods=['GET'])
def get_recommendations(user_id):
    """Get recommendations for user"""
    
@recommendations_bp.route('/<int:rec_id>/like', methods=['POST'])
def like_match(rec_id):
    """Mark recommendation as liked"""
    
@recommendations_bp.route('/<int:rec_id>/view', methods=['POST'])
def mark_viewed(rec_id):
    """Mark recommendation as viewed"""
```

### Testing for Phase 3

Create `backend/tests/test_routes.py`:
```python
def test_register_endpoint():
    """Test user registration"""
    
def test_login_endpoint():
    """Test login returns JWT token"""
    
def test_create_preferences():
    """Test preference creation"""
    
def test_find_roommates():
    """Test matching engine"""
    
def test_authentication_required():
    """Test protected endpoints require token"""
```

### Success Criteria ✓
- [ ] All routes implemented
- [ ] Authentication working (login/register)
- [ ] JWT tokens properly issued
- [ ] Routes validate input
- [ ] Error responses consistent
- [ ] Route tests pass
- [ ] Can call endpoints with curl/Postman

### Estimate: 2-3 days

---

## 🧠 PHASE 4: Multi-Agent Implementation (Est. 3-5 Days)

This is the CORE of the system. Each agent must be carefully implemented.

### Files to Create

#### 1. `backend/agents/user_profiling_agent.py`
**Purpose:** Agent 1 - Validate & normalize user input

```python
class UserProfilingAgent(BaseAgent):
    def __init__(self):
        super().__init__('UserProfilingAgent', '1.0')
    
    def execute(self, user_data=None, preference_data=None, **inputs):
        """
        Validates and normalizes user data
        
        Input: Raw user/preference dictionary
        Output: Validated, normalized data
        
        Validations:
        - Email format
        - Password strength
        - Budget ranges
        - Age constraints
        - Required fields
        """
        
        # 1. Check inputs
        is_valid, missing = self.validate_inputs(['data_type'], inputs)
        if not is_valid:
            return AgentResult(self.name, AgentStatus.ERROR, 
                             error=f"Missing: {missing}")
        
        # 2. Validate data
        try:
            if user_data:
                validated = self._validate_user(user_data)
            elif preference_data:
                validated = self._validate_preferences(preference_data)
            
            # 3. Log decision
            self.log_decision('user', validated.get('id'), 'validated_input')
            
            return AgentResult(self.name, AgentStatus.SUCCESS, validated)
        
        except ValueError as e:
            return AgentResult(self.name, AgentStatus.ERROR, error=str(e))
    
    def _validate_user(self, data):
        """Validate user registration data"""
        # Check email format
        # Check password strength (8+ chars, mixed case, number)
        # Check full_name not empty
        # etc.
        return normalized_data
    
    def _validate_preferences(self, data):
        """Validate preference form data"""
        # Budget_min < budget_max
        # Age_min < age_max
        # All enums valid
        # etc.
        return normalized_data
```

**Tests:**
```python
def test_valid_user_data():
def test_invalid_email():
def test_weak_password():
def test_prefer_validation():
```

#### 2. `backend/agents/preference_analysis_agent.py`
**Purpose:** Agent 2 - Convert preferences to vectors

```python
class PreferenceAnalysisAgent(BaseAgent):
    def __init__(self):
        super().__init__('PreferenceAnalysisAgent', '1.0')
    
    def execute(self, user_id=None, preferences=None, **inputs):
        """
        Converts raw preferences to numerical vectors
        
        Input: {budget_min, budget_max, cleanliness: 'Very Clean', ...}
        Output: {vector: [0.5, 0.8, ...], weights: {...}}
        
        Process:
        1. Map categorical values to numbers
        2. Normalize to 0-1 scale
        3. Create preference weights
        4. Compute vector norm
        """
        
        try:
            # 1. Map categories to numbers
            numeric_prefs = self._categoricalize_preferences(preferences)
            
            # 2. Build vector: [budget_norm, lifestyle_norm, ...]
            vector = self._build_vector(numeric_prefs)
            
            # 3. Compute weights (which preferences matter most?)
            weights = self._compute_weights(preferences)
            
            # 4. Normalize vector
            norm = self._compute_norm(vector)
            
            # 5. Cache result
            self.cache_result(f'vector_{user_id}', vector, ttl_seconds=2592000)
            
            return AgentResult(self.name, AgentStatus.SUCCESS, {
                'vector': vector,
                'norm': norm,
                'weights': weights
            })
        
        except Exception as e:
            return AgentResult(self.name, AgentStatus.ERROR, error=str(e))
    
    def _build_vector(self, numeric_prefs):
        """
        Create preference vector
        
        Format: [budget_norm, cleanliness_norm, schedule_norm, 
                 noise_norm, age_norm, location_norm]
        
        Example output: [0.6, 0.9, 0.7, 0.3, 0.5, 0.8]
        """
        pass
    
    def _compute_weights(self, preferences):
        """
        Determine preference weights
        
        If user set many hard constraints → increase their weight
        If flexible on something → lower weight
        
        Returns: {budget: 0.2, lifestyle: 0.4, ...}
        """
        pass
```

**Critical:** This agent determines how similarity is computed!

#### 3. `backend/agents/compatibility_scoring_agent.py`
**Purpose:** Agent 3 - Compute similarity scores

```python
class CompatibilityScoringAgent(BaseAgent):
    def __init__(self):
        super().__init__('CompatibilityScoringAgent', '1.0')
    
    def execute(self, user_a_id=None, user_b_id=None, 
                user_a_vector=None, user_b_vector=None, **inputs):
        """
        Computes compatibility score between two users
        
        Input: Two preference vectors
        Output: {overall_score, lifestyle_score, budget_score, ...}
        
        Algorithm:
        overall_score = 
            0.3 * cosine_similarity(vectors) +
            0.2 * lifestyle_match +
            0.2 * schedule_match +
            0.15 * budget_alignment +
            0.15 * habits_alignment
        """
        
        try:
            # 1. Compute cosine similarity
            cosine_sim = self._cosine_similarity(user_a_vector, user_b_vector)
            
            # 2. Compute component scores
            lifestyle = self._lifestyle_match(user_a_id, user_b_id)
            schedule = self._schedule_compatibility(user_a_id, user_b_id)
            budget = self._budget_alignment(user_a_id, user_b_id)
            habits = self._habits_alignment(user_a_id, user_b_id)
            
            # 3. Weighted combination
            overall = (
                0.3 * cosine_sim +
                0.2 * lifestyle +
                0.2 * schedule +
                0.15 * budget +
                0.15 * habits
            ) * 100  # Convert to 0-100 scale
            
            # 4. Store result (cache)
            score = CompatibilityScore(
                user_a_id=user_a_id,
                user_b_id=user_b_id,
                overall_score=overall,
                lifestyle_score=lifestyle * 100,
                schedule_score=schedule * 100,
                budget_score=budget * 100,
                habits_score=habits * 100
            )
            db.session.add(score)
            db.session.commit()
            
            self.log_decision('score', score.score_id, 'computed_score',
                            {'overall': overall})
            
            return AgentResult(self.name, AgentStatus.SUCCESS, {
                'overall_score': overall,
                'component_scores': {
                    'lifestyle': lifestyle * 100,
                    'schedule': schedule * 100,
                    'budget': budget * 100,
                    'habits': habits * 100,
                    'cosine_similarity': cosine_sim * 100
                }
            })
        
        except Exception as e:
            return AgentResult(self.name, AgentStatus.ERROR, error=str(e))
    
    def _cosine_similarity(self, vec_a, vec_b):
        """
        Cosine similarity between two vectors
        
        Formula: dot(A,B) / (||A|| * ||B||)
        Returns: 0-1 (higher = more similar)
        """
        import numpy as np
        a = np.array(vec_a)
        b = np.array(vec_b)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
```

**Key Metrics:**
- Cosine similarity (preference vectors)
- Lifestyle alignment (cleanliness, schedule, noise tolerance)
- Budget overlap (ranges intersect)
- Hard constraints (pets, smoking)

#### 4. `backend/agents/room_matching_agent.py`
**Purpose:** Agent 4 - Filter rooms by constraints

```python
class RoomMatchingAgent(BaseAgent):
    def execute(self, user_id=None, preferences=None, **inputs):
        """
        Filter available rooms by user preferences
        
        Input: User preferences
        Output: Ranked list of compatible rooms
        
        Filters:
        1. Location match
        2. Budget overlap
        3. Room type
        4. Amenities
        5. Availability
        """
        
        try:
            # 1. Get all available rooms
            rooms = Room.query.filter_by(is_available=True).all()
            
            # 2. Filter by constraints
            filtered_rooms = []
            for room in rooms:
                score = self._compute_room_match_score(room, preferences)
                if score >= 50:  # Threshold
                    filtered_rooms.append({
                        'room': room,
                        'match_score': score
                    })
            
            # 3. Sort by score (descending)
            filtered_rooms.sort(key=lambda x: x['match_score'], reverse=True)
            
            return AgentResult(self.name, AgentStatus.SUCCESS, filtered_rooms[:10])
        
        except Exception as e:
            return AgentResult(self.name, AgentStatus.ERROR, error=str(e))
    
    def _compute_room_match_score(self, room, preferences):
        """Score how well room matches user preferences"""
        score = 0
        
        # Location match (30%)
        if room.location == preferences['preferred_location']:
            score += 30
        
        # Budget overlap (40%)
        if (preferences['budget_min'] <= room.rent_price <= 
            preferences['budget_max']):
            score += 40
        
        # Room type match (20%)
        if room.room_type == preferences.get('preferred_room_type', 'Any'):
            score += 20
        
        # Other factors (10%)
        # ...
        
        return min(score, 100)
```

#### 5. `backend/agents/conflict_detection_agent.py`
**Purpose:** Agent 5 - Identify deal-breaker conflicts

```python
class ConflictDetectionAgent(BaseAgent):
    def execute(self, user_a_id=None, user_b_id=None, **inputs):
        """
        Detect conflicts that would prevent a match
        
        Hard Conflicts (Blockers):
        - User A has dog, User B forbids pets
        - User A smokes, User B forbids smoking
        - Budget ranges don't overlap
        
        Soft Conflicts (Warnings):
        - Schedule mismatch (9-5 vs night shift)
        - Extreme cleanliness gap
        - Large age difference
        """
        
        conflicts = []
        
        # Get preferences
        pref_a = get_user_preferences(user_a_id)
        pref_b = get_user_preferences(user_b_id)
        
        # Check HARD conflicts
        if self._has_pet_conflict(pref_a, pref_b):
            conflicts.append({
                'type': 'Hard',
                'description': 'Pet mismatch',
                'severity': 10
            })
        
        if self._has_smoking_conflict(pref_a, pref_b):
            conflicts.append({
                'type': 'Hard',
                'description': 'Smoking conflict',
                'severity': 10
            })
        
        if self._budget_no_overlap(pref_a, pref_b):
            conflicts.append({
                'type': 'Hard',
                'description': 'No budget overlap',
                'severity': 10
            })
        
        # Check SOFT conflicts
        if self._schedule_mismatch(pref_a, pref_b):
            conflicts.append({
                'type': 'Soft',
                'description': 'Schedule mismatch',
                'severity': 5
            })
        
        if self._cleanliness_gap(pref_a, pref_b):
            conflicts.append({
                'type': 'Soft',
                'description': 'Cleanliness gap',
                'severity': 4
            })
        
        # Log conflicts
        for conflict in conflicts:
            log = ConflictLog(
                user_a_id=user_a_id,
                user_b_id=user_b_id,
                conflict_type=conflict['type'],
                description=conflict['description'],
                severity=conflict['severity']
            )
            db.session.add(log)
        
        db.session.commit()
        
        return AgentResult(self.name, AgentStatus.SUCCESS, conflicts)
```

#### 6. `backend/agents/recommendation_engine_agent.py`
**Purpose:** Agent 6 - Rank matches with explanations

```python
class RecommendationEngineAgent(BaseAgent):
    def execute(self, requester_id=None, match_type='roommate', 
                candidate_ids=None, scores=None, conflicts_list=None, **inputs):
        """
        Rank matches and generate explanations
        
        Input: 
        - Requester ID
        - List of candidates with scores
        - Conflicts for each pair
        
        Output:
        - Ranked list [match1, match2, ...]
        - Each with:
          - Score
          - Explanation (WHY this match?)
          - Conflict warnings
        """
        
        try:
            recommendations = []
            
            for candidate_id, score, conflicts in zip(
                candidate_ids, scores, conflicts_list):
                
                # Filter out hard conflicts
                hard_conflicts = [c for c in conflicts if c['type'] == 'Hard']
                if hard_conflicts:
                    continue  # Skip this match
                
                # Generate explanation
                explanation = self._generate_explanation(
                    requester_id, candidate_id, score, conflicts)
                
                # Create recommendation
                rec = Recommendation(
                    requester_id=requester_id,
                    match_type=match_type,
                    match_id=candidate_id,
                    match_score=score,
                    explanation=explanation,
                    conflict_warnings=json.dumps([
                        c for c in conflicts if c['type'] == 'Soft'
                    ])
                )
                db.session.add(rec)
                
                recommendations.append({
                    'match_id': candidate_id,
                    'score': score,
                    'explanation': explanation,
                    'soft_warnings': soft_conflicts
                })
            
            db.session.commit()
            
            # Sort by score (descending) and return top 10
            recommendations.sort(key=lambda x: x['score'], reverse=True)
            
            return AgentResult(self.name, AgentStatus.SUCCESS,
                             recommendations[:10])
        
        except Exception as e:
            return AgentResult(self.name, AgentStatus.ERROR, error=str(e))
    
    def _generate_explanation(self, user_a_id, user_b_id, score, conflicts):
        """
        Generate human-readable explanation
        
        Format:
        "Jane (78/100): Both are very clean (8/10 & 9/10).
         Similar schedule (both 9-5). Budget overlap $550-700.
         WARNING: Different noise tolerance (3 vs 7)."
        """
        
        user_b = User.query.get(user_b_id)
        pref_b = UserPreference.query.filter_by(user_id=user_b_id).first()
        
        parts = [f"{user_b.full_name} ({score:.0f}/100):"]
        
        # Add positives
        parts.append("✓ Similar preferences")
        parts.append("✓ Budget overlap")
        
        # Add warnings
        soft = [c for c in conflicts if c['type'] == 'Soft']
        if soft:
            parts.append(f"⚠️  {soft[0]['description']}")
        
        return " ".join(parts)
```

#### 7. `backend/agents/agent_orchestrator.py`
**Purpose:** Controls the multi-agent workflow

```python
class AgentOrchestrator:
    """
    Orchestrates the 6-agent pipeline:
    User Data
      ↓
    [1. Profiling] → Validate
      ↓
    [2. Analysis] → Vectorize
      ↓
    [3. Scoring] → Compare
      ↓
    [4. Room/User Matching] → Filter
      ↓
    [5. Conflict Detection] → Check issues
      ↓
    [6. Recommendation] → Rank & explain
      ↓
    Final Matches
    """
    
    def __init__(self):
        self.agents = {
            'profiling': UserProfilingAgent(),
            'analysis': PreferenceAnalysisAgent(),
            'scoring': CompatibilityScoringAgent(),
            'room_matching': RoomMatchingAgent(),
            'conflict_detection': ConflictDetectionAgent(),
            'recommendation': RecommendationEngineAgent()
        }
    
    def find_roommate_matches(self, user_id):
        """
        Find roommate matches for a user
        
        Args:
            user_id: ID of user seeking matches
        
        Returns:
            List of recommended matches with scores & explanations
        """
        
        # STEP 1: Get user & preferences
        user = User.query.get(user_id)
        preferences = UserPreference.query.filter_by(user_id=user_id).first()
        
        # STEP 2: Ensure preferences are vectorized
        vector = self._get_or_create_vector(user_id, preferences)
        
        # STEP 3: Find candidate users (same city, similar budget)
        candidates = self._get_candidates(preferences)
        candidate_ids = [c.user_id for c in candidates]
        
        # STEP 4: Score all candidates
        scores = []
        conflicts_all = []
        
        for candidate_id in candidate_ids:
            if candidate_id == user_id:
                continue
            
            # Score compatibility
            score_result = self.agents['scoring'].execute(
                user_a_id=user_id,
                user_b_id=candidate_id,
                user_a_vector=vector,
                user_b_vector=self._get_vector(candidate_id)
            )
            
            if score_result.is_success():
                scores.append(score_result.data['overall_score'])
                
                # Detect conflicts
                conflict_result = self.agents['conflict_detection'].execute(
                    user_a_id=user_id,
                    user_b_id=candidate_id
                )
                
                if conflict_result.is_success():
                    conflicts_all.append(conflict_result.data)
        
        # STEP 5: Generate recommendations
        rec_result = self.agents['recommendation'].execute(
            requester_id=user_id,
            match_type='roommate',
            candidate_ids=candidate_ids,
            scores=scores,
            conflicts_list=conflicts_all
        )
        
        if rec_result.is_success():
            return rec_result.data
        else:
            return []
    
    def find_room_matches(self, user_id):
        """Find rooms matching user preferences"""
        
        prefs = UserPreference.query.filter_by(user_id=user_id).first()
        
        # Use Room Matching Agent
        result = self.agents['room_matching'].execute(
            user_id=user_id,
            preferences=prefs.to_dict()
        )
        
        return result.data if result.is_success() else []
```

### Testing for Phase 4

Create comprehensive tests:

```python
# backend/tests/test_agents.py

def test_profiling_agent_validates_input():
def test_analysis_agent_creates_vectors():
def test_scoring_agent_computes_similarity():
def test_room_matching_agent_filters():
def test_conflict_detection_finds_blockers():
def test_recommendation_engine_explains():
def test_orchestrator_pipeline():
```

### Key Concepts to Implement

1. **Vectorization**: Convert {budget_min: 500, cleanliness: 'Very Clean'} → [0.5, 0.9]
2. **Similarity Metrics**: Use cosine similarity from scikit-learn
3. **Weighted Scoring**: Different factors weighted differently
4. **Caching**: Store vectors & scores to avoid recomputation
5. **Explainability**: Every decision must be logged and explainable

### Success Criteria ✓
- [ ] All 6 agents implemented
- [ ] Each agent has execute() method
- [ ] Agents log decisions to audit_log
- [ ] Orchestrator can run pipeline
- [ ] Vectorization works
- [ ] Scoring algorithm correct
- [ ] Conflicts detected
- [ ] Recommendations ranked & explained
- [ ] All agent tests pass

### Estimate: 3-5 days (This is THE core of the system!)

---

## 🎨 PHASE 5: Frontend UI (Est. 2-3 Days)

### Objective
Create HTML/CSS/JavaScript pages that let users interact with the system.

### Files to Create

#### 1. `frontend/index.html` - Landing Page
- Navigation menu
- "Get Started" button → Register
- Overview of system

#### 2. `frontend/register.html` - Registration
- Form: email, password, full_name, gender
- Validation feedback
- Submit → /auth/register

#### 3. `frontend/login.html` - Login  
- Form: email, password
- JWT token storage
- Redirect to dashboard

#### 4. `frontend/dashboard.html` - Main Page
- User greeting
- Navigation to:
  - View/Edit Profile
  - Complete Preferences
  - View Matches
  - Search Rooms
- Show stats (matches found, etc.)

#### 5. `frontend/preferences.html` - Preference Form
- Budget slider (min-max)
- Location dropdown
- Gender preference radio
- Cleanliness level
- Work schedule
- Checkboxes: smoking, pets
- Noise tolerance slider
- Submit → /preferences

#### 6. `frontend/matches.html` - Match Results
- Display top 10 matches
- For each match:
  - Photo
  - Name, age, city
  - Score (87/100)
  - Score breakdown
  - Explanation
  - Conflict warnings
  - "Like" button
- Sort/Filter options

#### 7. `frontend/rooms.html` - Room Search
- Filters: location, price range, room type, amenities
- Search results as cards
- Click for details → room-detail.html
- Add to favorites

#### 8. `frontend/css/style.css`
- Color scheme
- Typography
- Layout
- Component styling

#### 9. `frontend/js/api.js`
- Fetch wrapper
- Token management
- Error handling

#### 10. `frontend/js/auth.js`
- Login/register logic
- Token storage
- Protected route checking

### Frontend Architecture

```
frontend/
├── index.html              (Landing, navigation)
├── register.html           (Registration form)
├── login.html               (Login form)
├── dashboard.html          (Main page)
├── preferences.html        (Preference form)
├── matches.html            (Match results)
├── rooms.html              (Room search)
├── room-detail.html        (Single room)
├── profile.html            (User profile)
│
├── css/
│   ├── style.css           (Main styles)
│   ├── responsive.css      (Mobile friendly)
│   └── theme.css           (Colors, fonts)
│
├── js/
│   ├── main.js             (Load balancer)
│   ├── auth.js             (Auth logic)
│   ├── api.js              (API client)
│   ├── preferences.js      (Preference form)
│   ├── matches.js          (Match display)
│   ├── rooms.js            (Room display)
│   └── utils.js            (Helpers)
│
└── images/
    └── (logos, icons, etc.)
```

### Key Features

**Responsive Design:**
- Works on mobile, tablet, desktop
- Hamburger menu for mobile

**Accessibility:**
- ARIA labels
- Keyboard navigation
- Color contrast

**User Experience:**
- Form validation with feedback
- Loading spinners
- Error messages
- Success confirmations

### Example: Matches Page Flow

```javascript
// frontend/js/matches.js

async function loadMatches() {
    // 1. Get user ID from token
    const userId = getCurrentUserId();
    
    // 2. Call backend
    const response = await api.get(`/matches/roommates/${userId}`);
    
    // 3. Display results
    if (response.success) {
        const matches = response.data;
        matches.forEach(match => {
            displayMatchCard(match);
        });
    } else {
        showError(response.error);
    }
}

function displayMatchCard(match) {
    // Create HTML card with match info
    const card = `
        <div class="match-card">
            <img src="${match.photo}" alt="${match.name}">
            <h3>${match.name}, ${match.age}</h3>
            <div class="score">${match.score}/100</div>
            <p>${match.explanation}</p>
            <button onclick="likeMatch(${match.id})">✓ Like</button>
        </div>
    `;
    
    document.getElementById('matches-container').innerHTML += card;
}

async function likeMatch(matchId) {
    await api.post(`/recommendations/${matchId}/like`);
    showSuccess("Liked!");
}
```

### Success Criteria ✓
- [ ] All pages created and linked
- [ ] Forms submit correctly
- [ ] API calls work
- [ ] Token handling working
- [ ] Responsive design
- [ ] No console errors
- [ ] Mobile friendly

### Estimate: 2-3 days

---

## 🧪 PHASE 6: Testing & Deployment (Est. 1-2 Days)

### Unit Tests
```bash
pytest backend/tests/test_models.py
pytest backend/tests/test_agents.py
pytest backend/tests/test_routes.py
```

**Target:** 80%+ code coverage

### Integration Tests
```bash
pytest backend/tests/test_integration.py
# Test complete flow: register → preferences → find matches
```

### Manual Testing
1. Register new account
2. Complete preference form
3. Find roommate matches
4. View match explanations
5. Search for rooms
6. Test error cases

### Docker Deployment
```bash
docker build -t roommate-matching .
docker run -p 5000:5000 roommate-matching
```

### Deployment Checklist
- [ ] Tested with PostgreSQL
- [ ] Environment variables configured
- [ ] HTTPS enabled
- [ ] Database backups working
- [ ] Error logging working
- [ ] Performance acceptable
- [ ] Documentation complete

---

## 📊 Overall Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| Phase 1: Foundation | 1 day | ✅ DONE |
| Phase 2: Models | 1-2 days | ⏳ Next |
| Phase 3: Routes | 2-3 days | |
| Phase 4: Agents | 3-5 days | (Core work!) |
| Phase 5: Frontend | 2-3 days | |
| Phase 6: Testing | 1-2 days | |
| **Total** | **10-16 days** | |

**Buffer:** Add 2-3 days for debugging/refinement

---

## ✅ Success = This Checklist

- [ ] System fully functional
- [ ] All 6 agents implemented & tested
- [ ] User can register, set preferences, find matches
- [ ] Matches have scores & explanations
- [ ] Code is clean & commented
- [ ] Documentation is complete
- [ ] Tests pass
- [ ] Deployable via Docker
- [ ] Can explain to examiner

---

**Status**: Phase 1 ✅ | Phase 2 ⏳ Ready to Start

Ready to proceed with Phase 2 (Models)? 🚀
