-- Roommate Matching System - Database Schema
-- SQLite + PostgreSQL compatible
-- This schema defines all tables for the multi-agent system

-- ============================================================================
-- USERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    gender ENUM('M', 'F', 'Other'),
    city VARCHAR(100),
    phone VARCHAR(20),
    profile_picture VARCHAR(500),
    bio TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CHECK (length(email) > 0),
    CHECK (length(password_hash) > 0)
);

-- Index for faster lookups
CREATE UNIQUE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_city ON users(city);


-- ============================================================================
-- USER PREFERENCES TABLE
-- Stores user's matching preferences for roommate matching
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_preferences (
    preference_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    
    -- Budget Preferences
    budget_min DECIMAL(8,2) NOT NULL,
    budget_max DECIMAL(8,2) NOT NULL,
    
    -- Location & Basic Info
    preferred_location VARCHAR(200),
    gender_preference ENUM('M', 'F', 'Any') DEFAULT 'Any',
    age_min INTEGER,
    age_max INTEGER,
    
    -- Lifestyle Preferences
    cleanliness_level ENUM('Very Clean', 'Clean', 'Average', 'Relaxed'),
    schedule ENUM('9-5 Job', 'Night Shift', 'Student', 'Flexible'),
    
    -- Hard Constraints
    smoking_ok BOOLEAN DEFAULT FALSE,
    pets_ok BOOLEAN DEFAULT FALSE,
    
    -- Soft Preferences
    noise_tolerance INTEGER CHECK (noise_tolerance >= 1 AND noise_tolerance <= 10),
    preferred_room_type ENUM('Single', 'Shared', 'Any'),
    lease_duration_months INTEGER,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CHECK (budget_min <= budget_max),
    CHECK (age_min <= age_max)
);

CREATE INDEX idx_preferences_user ON user_preferences(user_id);


-- ============================================================================
-- PREFERENCE VECTORS TABLE
-- Stores vectorized/normalized preferences for similarity computation
-- Used by: Preference Analysis Agent, Compatibility Scoring Agent
-- ============================================================================
CREATE TABLE IF NOT EXISTS preference_vectors (
    vector_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    
    -- Vectorized preference data (JSON format)
    -- Format: [budget_norm, cleanliness_norm, schedule_norm, ...]
    vector_data JSON NOT NULL,
    
    -- Euclidean norm of the vector (for cosine similarity calculation)
    vector_norm DECIMAL(10,4) NOT NULL,
    
    -- Preference weights (JSON format)
    -- Format: {"budget": 0.2, "lifestyle": 0.4, "schedule": 0.3, ...}
    preference_weights JSON,
    
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX idx_vectors_user ON preference_vectors(user_id);


-- ============================================================================
-- ROOMS TABLE
-- Stores available room listings
-- Posted by: Property owners / landlords
-- ============================================================================
CREATE TABLE IF NOT EXISTS rooms (
    room_id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL,
    
    -- Basic Info
    title VARCHAR(255) NOT NULL,
    description TEXT,
    location VARCHAR(200) NOT NULL,
    
    -- Rental Details
    rent_price DECIMAL(8,2) NOT NULL,
    room_type ENUM('Single', 'Shared', 'Master') NOT NULL,
    bedrooms INTEGER,
    bathrooms DECIMAL(3,1),
    
    -- Room Features (stored as JSON array)
    -- Example: ["WiFi", "AC", "Kitchen access", "Balcony"]
    amenities JSON,
    
    -- Occupancy Rules
    smoking_allowed BOOLEAN DEFAULT FALSE,
    pets_allowed BOOLEAN DEFAULT FALSE,
    
    -- Images (JSON array of URLs or file paths)
    images JSON,
    
    -- Availability
    is_available BOOLEAN DEFAULT TRUE,
    available_from DATE,
    lease_duration_months INTEGER,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (owner_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CHECK (rent_price > 0)
);

CREATE INDEX idx_rooms_location ON rooms(location);
CREATE INDEX idx_rooms_owner ON rooms(owner_id);
CREATE INDEX idx_rooms_available ON rooms(is_available);


-- ============================================================================
-- COMPATIBILITY SCORES TABLE
-- Stores cached computation results from Compatibility Scoring Agent
-- Used for performance optimization (avoid recomputing same pairs)
-- ============================================================================
CREATE TABLE IF NOT EXISTS compatibility_scores (
    score_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_a_id INTEGER NOT NULL,
    user_b_id INTEGER NOT NULL,
    
    -- Overall composite score (0-100)
    overall_score DECIMAL(5,2) NOT NULL,
    
    -- Component scores (each 0-100)
    lifestyle_score DECIMAL(5,2),
    budget_score DECIMAL(5,2),
    schedule_score DECIMAL(5,2),
    habits_score DECIMAL(5,2),
    age_match_score DECIMAL(5,2),
    
    -- Computation metadata
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_a_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (user_b_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE (user_a_id, user_b_id),
    CHECK (overall_score >= 0 AND overall_score <= 100)
);

CREATE INDEX idx_scores_user_a ON compatibility_scores(user_a_id);
CREATE INDEX idx_scores_user_b ON compatibility_scores(user_b_id);


-- ============================================================================
-- CONFLICT LOG TABLE
-- Records conflicts detected by Conflict Detection Agent
-- Hard conflicts = deal breakers (pets, smoking, budget mismatch)
-- Soft conflicts = warnings (schedule mismatch, cleanliness gap)
-- ============================================================================
CREATE TABLE IF NOT EXISTS conflict_log (
    conflict_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_a_id INTEGER,
    user_b_id INTEGER,
    room_id INTEGER,
    
    -- Conflict Classification
    conflict_type ENUM('Hard', 'Soft') NOT NULL,
    
    -- Details
    description TEXT NOT NULL,
    severity INTEGER CHECK (severity >= 1 AND severity <= 10),
    
    -- Metadata
    auto_generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_a_id) REFERENCES users(user_id) ON DELETE SET NULL,
    FOREIGN KEY (user_b_id) REFERENCES users(user_id) ON DELETE SET NULL,
    FOREIGN KEY (room_id) REFERENCES rooms(room_id) ON DELETE SET NULL
);

CREATE INDEX idx_conflicts_users ON conflict_log(user_a_id, user_b_id);
CREATE INDEX idx_conflicts_room ON conflict_log(room_id);


-- ============================================================================
-- RECOMMENDATIONS TABLE
-- Stores match recommendations generated by Recommendation Engine Agent
-- Tracks which matches were shown to users and their interaction
-- ============================================================================
CREATE TABLE IF NOT EXISTS recommendations (
    recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    requester_id INTEGER NOT NULL,
    match_type ENUM('roommate', 'room') NOT NULL,
    match_id INTEGER NOT NULL,  -- user_id if roommate, room_id if room
    
    -- Score & Details
    match_score DECIMAL(5,2) NOT NULL,
    
    -- Explanation from Recommendation Engine
    -- Contains: score breakdown, why recommended, warnings, etc.
    explanation TEXT,
    
    -- Conflict warnings (JSON)
    conflict_warnings JSON,
    
    -- User Interaction
    viewed_at TIMESTAMP,
    liked BOOLEAN DEFAULT NULL,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (requester_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CHECK (match_score >= 0 AND match_score <= 100)
);

CREATE INDEX idx_recommendations_requester ON recommendations(requester_id);
CREATE INDEX idx_recommendations_match ON recommendations(match_type, match_id);
CREATE INDEX idx_recommendations_created ON recommendations(created_at);


-- ============================================================================
-- INTERACTIONS TABLE
-- Tracks user interactions: likes, messages, mutual matches
-- Used for future messaging and analytics features
-- ============================================================================
CREATE TABLE IF NOT EXISTS interactions (
    interaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_a_id INTEGER NOT NULL,
    user_b_id INTEGER NOT NULL,
    
    interaction_type ENUM('like', 'unlike', 'message', 'view') NOT NULL,
    interaction_data JSON,  -- Additional context (e.g., message content, timestamp)
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_a_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (user_b_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX idx_interactions_users ON interactions(user_a_id, user_b_id);
CREATE INDEX idx_interactions_type ON interactions(interaction_type);


-- ============================================================================
-- ANALYTICS TABLE
-- Stores aggregated data for dashboard insights
-- Used for analytics and system monitoring
-- ============================================================================
CREATE TABLE IF NOT EXISTS analytics (
    analytics_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    
    event_type VARCHAR(100) NOT NULL,
    event_data JSON,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX idx_analytics_user ON analytics(user_id);
CREATE INDEX idx_analytics_event ON analytics(event_type);


-- ============================================================================
-- AUDIT LOG TABLE
-- Logs all agent decisions for transparency and debugging
-- Helps explain WHY the system made a particular decision
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name VARCHAR(100) NOT NULL,
    action VARCHAR(255) NOT NULL,
    entity_type VARCHAR(50),  -- 'user', 'room', 'score', etc.
    entity_id INTEGER,
    
    details TEXT,  -- JSON with details of action
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_agent ON audit_log(agent_name);
CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);


-- ============================================================================
-- VIEW: MUTUAL MATCHES
-- Shows users who have 'liked' each other
-- ============================================================================
CREATE VIEW IF NOT EXISTS mutual_matches AS
SELECT 
    l1.user_a_id as user_1_id,
    l1.user_b_id as user_2_id,
    l1.created_at as matched_at
FROM interactions l1
JOIN interactions l2 
    ON l1.user_a_id = l2.user_b_id 
    AND l1.user_b_id = l2.user_a_id
    AND l1.interaction_type = 'like'
    AND l2.interaction_type = 'like'
GROUP BY l1.user_a_id, l1.user_b_id;


-- ============================================================================
-- VIEW: USER STATS
-- Summary statistics for each user
-- ============================================================================
CREATE VIEW IF NOT EXISTS user_stats AS
SELECT 
    u.user_id,
    u.full_name,
    COUNT(DISTINCT r.recommendation_id) as recommendations_received,
    COUNT(DISTINCT CASE WHEN r.liked = TRUE THEN r.recommendation_id END) as likes_given,
    COUNT(DISTINCT i.interaction_id) as total_interactions,
    COUNT(DISTINCT CASE WHEN i.interaction_type = 'message' THEN i.interaction_id END) as messages_sent,
    u.created_at
FROM users u
LEFT JOIN recommendations r ON u.user_id = r.requester_id
LEFT JOIN interactions i ON u.user_id = i.user_a_id
GROUP BY u.user_id;


-- ============================================================================
-- SAMPLE DATA (for testing, comment out for production)
-- ============================================================================

-- Insert sample users for testing
INSERT INTO users (email, password_hash, full_name, gender, city, bio) VALUES
('alice@example.com', 'hashed_password_1', 'Alice Johnson', 'F', 'New York', 'Looking for a clean roommate'),
('bob@example.com', 'hashed_password_2', 'Bob Smith', 'M', 'New York', 'Student, quiet person'),
('charlie@example.com', 'hashed_password_3', 'Charlie Brown', 'M', 'New York', 'Software engineer'),
('diana@example.com', 'hashed_password_4', 'Diana Prince', 'F', 'New York', 'Yoga instructor');

-- Insert sample preferences
INSERT INTO user_preferences (user_id, budget_min, budget_max, preferred_location, cleanliness_level, schedule, smoking_ok, pets_ok, noise_tolerance) VALUES
(1, 500, 800, 'Manhattan', 'Very Clean', '9-5 Job', FALSE, FALSE, 3),
(2, 400, 700, 'Brooklyn', 'Clean', 'Student', FALSE, FALSE, 4),
(3, 600, 900, 'Manhattan', 'Average', '9-5 Job', FALSE, FALSE, 6),
(4, 500, 750, 'Brooklyn', 'Very Clean', 'Flexible', FALSE, TRUE, 2);

-- Insert sample rooms
INSERT INTO rooms (owner_id, title, description, location, rent_price, room_type, is_available, available_from) VALUES
(1, 'Cozy Manhattan Room', 'Spacious room with NYC view', 'Manhattan', 650.00, 'Single', TRUE, '2026-03-01'),
(3, 'Brooklyn Shared Room', '2BR apartment, seeking roommate', 'Brooklyn', 550.00, 'Shared', TRUE, '2026-02-28'),
(2, 'Studio Apartment', 'Small but charming studio', 'Manhattan', 750.00, 'Single', FALSE, '2026-04-01');

-- ============================================================================
-- END OF SCHEMA
-- Last Updated: February 24, 2026
-- ============================================================================
