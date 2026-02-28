"""
User Preferences Models
Stores user matching preferences and vectorized data for similarity computation.

Two tables:
1. user_preferences: Raw preference data (budget, lifestyle, etc.)
2. preference_vectors: Vectorized/normalized preferences for scoring
"""

from datetime import datetime
from sqlalchemy import Float, JSON, Integer, String, Boolean, Numeric, Enum
from sqlalchemy.orm import relationship
from backend.database import db


class UserPreference(db.Model):
    """
    Raw user preferences for roommate/room matching
    
    Stores what the user is looking for:
    - Budget range
    - Location preferences
    - Lifestyle (cleanliness, schedule, noise tolerance)
    - Hard constraints (pets, smoking)
    - Room type preferences
    
    Attributes:
        preference_id: Unique identifier
        user_id: Reference to user (one-to-one)
        budget_min/max: Price range for rent
        preferred_location: City/area preferences
        gender_preference: Prefer M/F/Any roommate
        age_min/max: Age range for roommate
        cleanliness_level: How clean they want living space
        schedule: Work schedule type
        smoking_ok: Whether smoking is acceptable
        pets_ok: Whether pets are acceptable
        noise_tolerance: How much noise they can tolerate (1-10)
        preferred_room_type: Single/Shared/Any
        lease_duration_months: Preferred lease length
    """
    
    __tablename__ = 'user_preferences'
    
    # Primary Key & Foreign Key
    preference_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), 
                       unique=True, nullable=False, index=True)
    
    # Budget Constraints
    budget_min = db.Column(db.Numeric(8, 2), nullable=False)
    budget_max = db.Column(db.Numeric(8, 2), nullable=False)
    
    # Location & Demographics
    preferred_location = db.Column(db.String(200))
    gender_preference = db.Column(db.Enum('M', 'F', 'Any'), default='Any')
    age_min = db.Column(db.Integer)
    age_max = db.Column(db.Integer)
    
    # Lifestyle Preferences
    cleanliness_level = db.Column(
        db.Enum('Very Clean', 'Clean', 'Average', 'Relaxed'),
        nullable=True
    )
    schedule = db.Column(
        db.Enum('9-5 Job', 'Night Shift', 'Student', 'Flexible'),
        nullable=True
    )
    
    # Hard Constraints (deal breakers)
    smoking_ok = db.Column(db.Boolean, default=False)
    pets_ok = db.Column(db.Boolean, default=False)
    
    # Soft Preferences
    noise_tolerance = db.Column(db.Integer)  # 1-10 scale
    preferred_room_type = db.Column(
        db.Enum('Single', 'Shared', 'Any'),
        default='Any'
    )
    lease_duration_months = db.Column(db.Integer)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, 
                          onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship('User', back_populates='preferences')
    vectors = relationship('PreferenceVector', back_populates='preference',
                          cascade='all, delete-orphan', uselist=False)
    
    def __repr__(self):
        return f'<UserPreference user_id={self.user_id}>'
    
    def to_dict(self):
        """
        Convert preferences to dictionary
        
        Returns:
            dict: All preference data
        """
        return {
            'preference_id': self.preference_id,
            'user_id': self.user_id,
            'budget_min': float(self.budget_min) if self.budget_min else None,
            'budget_max': float(self.budget_max) if self.budget_max else None,
            'preferred_location': self.preferred_location,
            'gender_preference': self.gender_preference,
            'age_min': self.age_min,
            'age_max': self.age_max,
            'cleanliness_level': self.cleanliness_level,
            'schedule': self.schedule,
            'smoking_ok': self.smoking_ok,
            'pets_ok': self.pets_ok,
            'noise_tolerance': self.noise_tolerance,
            'preferred_room_type': self.preferred_room_type,
            'lease_duration_months': self.lease_duration_months,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
    
    def validate(self):
        """
        Validate preference constraints
        
        Returns:
            tuple: (is_valid: bool, errors: list)
        """
        errors = []
        
        if not self.budget_min or not self.budget_max:
            errors.append('Budget range is required')
        elif float(self.budget_min) > float(self.budget_max):
            errors.append('Budget min must be less than max')
        elif float(self.budget_min) <= 0:
            errors.append('Budget must be positive')
        
        if self.age_min and self.age_max:
            if self.age_min > self.age_max:
                errors.append('Age min must be less than max')
            if self.age_min < 18:
                errors.append('Minimum age must be 18+')
        
        if self.noise_tolerance:
            if not (1 <= self.noise_tolerance <= 10):
                errors.append('Noise tolerance must be between 1-10')
        
        return len(errors) == 0, errors
    
    def get_vector(self):
        """
        Get vectorized preferences (for similarity computation)
        
        Returns:
            list: Preference vector, or None if not yet vectorized
        
        Example:
            vector = preferences.get_vector()
            if vector:
                similarity = cosine_similarity(vector, other_vector)
        """
        if self.vectors:
            return self.vectors.vector_data
        return None
    
    def has_vector(self):
        """Check if preferences have been vectorized"""
        return self.vectors is not None


class PreferenceVector(db.Model):
    """
    Vectorized user preferences for similarity computation
    
    Stores the numerical representation of preferences used by
    the Preference Analysis Agent for computing compatibility scores.
    
    Vector format: [budget_norm, cleanliness_norm, schedule_norm, 
                    noise_norm, age_norm, location_norm, ...]
    
    Each component is normalized to 0-1 scale.
    
    Attributes:
        vector_id: Unique identifier
        user_id: Reference to user
        vector_data: JSON array of floats (the actual vector)
        vector_norm: Euclidean norm (for cosine similarity)
        preference_weights: JSON dict of component weights
        computed_at: When vector was computed
    """
    
    __tablename__ = 'preference_vectors'
    
    # Primary Key
    vector_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_preferences.user_id'),
                       unique=True, nullable=False, index=True)
    
    # Vector Data
    vector_data = db.Column(db.JSON, nullable=False)  # [0.5, 0.8, 0.3, ...]
    vector_norm = db.Column(db.Numeric(10, 4), nullable=False)  # For cosine sim
    
    # Weights indicating which preferences matter most
    # Example: {"budget": 0.3, "lifestyle": 0.4, "schedule": 0.3}
    preference_weights = db.Column(db.JSON)
    
    # When computed
    computed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    preference = relationship('UserPreference', back_populates='vectors')
    
    def __repr__(self):
        return f'<PreferenceVector user_id={self.user_id}>'
    
    def to_dict(self):
        """
        Convert vector to dictionary
        
        Returns:
            dict: Vector data with metadata
        """
        return {
            'vector_id': self.vector_id,
            'user_id': self.user_id,
            'vector_data': self.vector_data,
            'vector_norm': float(self.vector_norm),
            'preference_weights': self.preference_weights,
            'computed_at': self.computed_at.isoformat(),
        }
    
    def get_similarity_with(self, other_vector):
        """
        Compute cosine similarity with another vector
        
        Args:
            other_vector: PreferenceVector instance or list
        
        Returns:
            float: Similarity score (0-1)
        
        Example:
            similarity = vec1.get_similarity_with(vec2)
            # Returns: 0.85 (85% similar)
        """
        import numpy as np
        
        if isinstance(other_vector, PreferenceVector):
            other_data = other_vector.vector_data
            other_norm = float(other_vector.vector_norm)
        else:
            other_data = other_vector
            other_norm = np.linalg.norm(other_data)
        
        if self.vector_norm == 0 or other_norm == 0:
            return 0.0
        
        a = np.array(self.vector_data)
        b = np.array(other_data)
        
        # Cosine similarity: dot(A,B) / (||A|| * ||B||)
        similarity = np.dot(a, b) / (float(self.vector_norm) * other_norm)
        return max(0.0, min(1.0, similarity))  # Clamp to [0, 1]
    
    def is_stale(self, max_age_days=30):
        """
        Check if vector is older than threshold
        Vectors may become stale if user hasn't interacted recently
        
        Args:
            max_age_days: Consider vector stale after this many days
        
        Returns:
            bool: True if vector should be recomputed
        """
        from datetime import timedelta
        age = datetime.utcnow() - self.computed_at
        return age > timedelta(days=max_age_days)
