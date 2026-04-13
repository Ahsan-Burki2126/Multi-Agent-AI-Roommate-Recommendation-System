"""
Compatibility Score Model
Stores cached compatibility scores between users.

Used by Compatibility Scoring Agent to store results,
avoiding redundant recalculation of the same pairs.
"""

from datetime import datetime
from sqlalchemy import Integer, Numeric, DateTime, UniqueConstraint, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import db


class CompatibilityScore(db.Model):
    """
    Cached compatibility score between two users
    
    This table stores computation results from the
    Compatibility Scoring Agent. It's used to avoid
    recalculating the same pair multiple times.
    
    Computed Score Formula:
        overall_score = 
            0.3 * cosine_similarity(preference_vectors) +
            0.2 * lifestyle_match_score +
            0.2 * schedule_compatibility_score +
            0.15 * budget_alignment_score +
            0.15 * habits_alignment_score
    
    Each component is 0-100, resulting overall is 0-100.
    
    Attributes:
        score_id: Unique identifier
        user_a_id: First user in pairing
        user_b_id: Second user in pairing
        overall_score: Final composite score (0-100)
        lifestyle_score: Cleanliness, habits compatibility
        budget_score: Price range overlap
        schedule_score: Work schedule compatibility
        habits_score: Smoking, pets, noise tolerance match
        age_match_score: Age range overlap
        computed_at: When this score was calculated
    """
    
    __tablename__ = 'compatibility_scores'
    
    # Primary Key
    score_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # User Pairing
    user_a_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), 
                         nullable=False, index=True)
    user_b_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), 
                         nullable=False, index=True)
    
    # Scores (all 0-100 scale)
    overall_score = db.Column(db.Numeric(5, 2), nullable=False)
    lifestyle_score = db.Column(db.Numeric(5, 2))
    budget_score = db.Column(db.Numeric(5, 2))
    schedule_score = db.Column(db.Numeric(5, 2))
    habits_score = db.Column(db.Numeric(5, 2))
    age_match_score = db.Column(db.Numeric(5, 2))
    
    # Metadata
    computed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Ensure unique pairing (only one score per pair)
    __table_args__ = (
        UniqueConstraint('user_a_id', 'user_b_id', 
                        name='unique_user_pair'),
    )
    
    # Relationships
    user_a = relationship('User', foreign_keys=[user_a_id])
    user_b = relationship('User', foreign_keys=[user_b_id])
    
    def __repr__(self):
        return f'<Score {self.user_a_id}-{self.user_b_id}: {self.overall_score}/100>'
    
    def to_dict(self):
        """
        Convert score to dictionary
        
        Returns:
            dict: All score components
        """
        return {
            'score_id': self.score_id,
            'user_a_id': self.user_a_id,
            'user_b_id': self.user_b_id,
            'overall_score': float(self.overall_score),
            'components': {
                'lifestyle': float(self.lifestyle_score) if self.lifestyle_score else None,
                'budget': float(self.budget_score) if self.budget_score else None,
                'schedule': float(self.schedule_score) if self.schedule_score else None,
                'habits': float(self.habits_score) if self.habits_score else None,
                'age_match': float(self.age_match_score) if self.age_match_score else None,
            },
            'computed_at': self.computed_at.isoformat(),
        }
    
    def to_summary(self):
        """
        Return simplified score summary
        
        Returns:
            dict: Overall score and components only
        """
        return {
            'overall_score': float(self.overall_score),
            'lifestyle_score': float(self.lifestyle_score) if self.lifestyle_score else None,
            'budget_score': float(self.budget_score) if self.budget_score else None,
            'schedule_score': float(self.schedule_score) if self.schedule_score else None,
            'habits_score': float(self.habits_score) if self.habits_score else None,
        }
    
    def get_component_breakdown(self):
        """
        Get breakdown of all score components
        
        Returns:
            dict: Detailed breakdown of each component's contribution
        
        Example:
            breakdown = score.get_component_breakdown()
            # Returns:
            # {
            #     'overall_score': 78.5,
            #     'lifestyle_match': 82.0,
            #     'budget_alignment': 75.0,
            #     'schedule_compatibility': 70.0,
            #     'habits_match': 80.0,
            #     'age_compatibility': 85.0
            # }
        """
        return {
            'overall_score': float(self.overall_score),
            'lifestyle_match': float(self.lifestyle_score) if self.lifestyle_score else None,
            'budget_alignment': float(self.budget_score) if self.budget_score else None,
            'schedule_compatibility': float(self.schedule_score) if self.schedule_score else None,
            'habits_compatibility': float(self.habits_score) if self.habits_score else None,
            'age_compatibility': float(self.age_match_score) if self.age_match_score else None,
        }
    
    def is_above_threshold(self, threshold=50):
        """
        Check if overall score meets minimum threshold
        
        Args:
            threshold: Minimum acceptable score (default=50)
        
        Returns:
            bool: True if score >= threshold
        
        Example:
            if compatibility.is_above_threshold(70):
                # Good match
        """
        return float(self.overall_score) >= threshold
    
    def get_strength_description(self):
        """
        Get human-readable description of match strength
        
        Returns:
            str: Description like "Excellent Match", "Good Match", etc.
        """
        score = float(self.overall_score)
        
        if score >= 85:
            return "Excellent Match"
        elif score >= 70:
            return "Very Good Match"
        elif score >= 60:
            return "Good Match"
        elif score >= 50:
            return "Fair Match"
        elif score >= 40:
            return "Possible Match"
        else:
            return "Poor Match"
    
    def get_strongest_component(self):
        """
        Return which component is the strongest.
        Only considers components that were actually computed (not None).

        Returns:
            tuple: (component_name: str, score: float) or (None, None) if no scores
        """
        components = {
            name: float(val)
            for name, val in [
                ('lifestyle', self.lifestyle_score),
                ('budget', self.budget_score),
                ('schedule', self.schedule_score),
                ('habits', self.habits_score),
                ('age_match', self.age_match_score),
            ]
            if val is not None
        }
        if not components:
            return None, None
        strongest = max(components, key=components.get)
        return strongest, components[strongest]

    def get_weakest_component(self):
        """
        Return which component has the lowest score.
        Only considers components that were actually computed (not None).

        Returns:
            tuple: (component_name: str, score: float) or (None, None) if no scores
        """
        components = {
            name: float(val)
            for name, val in [
                ('lifestyle', self.lifestyle_score),
                ('budget', self.budget_score),
                ('schedule', self.schedule_score),
                ('habits', self.habits_score),
                ('age_match', self.age_match_score),
            ]
            if val is not None
        }
        if not components:
            return None, None
        weakest = min(components, key=components.get)
        return weakest, components[weakest]
    
    @staticmethod
    def get_score_for_pair(user_a_id, user_b_id):
        """
        Lookup compatibility score for a user pair
        
        Args:
            user_a_id: First user ID
            user_b_id: Second user ID
        
        Returns:
            CompatibilityScore object if exists, None otherwise
        
        Example:
            score = CompatibilityScore.get_score_for_pair(1, 2)
            if score:
                print(f"Compatibility: {score.overall_score}/100")
        """
        # Try both directions (A-B and B-A)
        score = CompatibilityScore.query.filter(
            ((CompatibilityScore.user_a_id == user_a_id) & 
             (CompatibilityScore.user_b_id == user_b_id)) |
            ((CompatibilityScore.user_a_id == user_b_id) & 
             (CompatibilityScore.user_b_id == user_a_id))
        ).first()
        
        return score
    
    def is_stale(self, max_age_days=7):
        """
        Check if score is older than threshold
        Stale scores should be recomputed
        
        Args:
            max_age_days: Consider stale after this many days
        
        Returns:
            bool: True if score should be recomputed
        """
        from datetime import timedelta
        age = datetime.utcnow() - self.computed_at
        return age > timedelta(days=max_age_days)
