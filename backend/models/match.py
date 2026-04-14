"""
Recommendation Model
Stores match recommendations shown to users.

Records what matches were presented to users,
how they interacted with them, and the explanations provided.
"""

from datetime import datetime
from sqlalchemy import Integer, String, Numeric, Text, JSON, Boolean, DateTime, Enum
from backend.database import db


class Recommendation(db.Model):
    """
    Match recommendation shown to a user
    
    When the Recommendation Engine Agent runs,
    it creates Recommendation records for each match found,
    storing the score, explanation, and tracking user interactions.
    
    This allows us to:
    - Track what matches were recommended
    - Measure engagement (views, likes)
    - Learn what explanations work well
    - Audit recommendations for bias/fairness
    
    Attributes:
        recommendation_id: Unique identifier
        requester_id: User receiving the recommendation
        match_type: 'roommate' or 'room'
        match_id: ID of the recommended user or room
        match_score: Compatibility score (0-100)
        explanation: Why this match was recommended
        conflict_warnings: Any soft conflicts
        viewed_at: When user viewed this recommendation
        liked: User's response (True/False/None)
        created_at: When recommendation was created
    """
    
    __tablename__ = 'recommendations'
    
    # Primary Key
    recommendation_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # User & Match Info
    requester_id = db.Column(db.Integer, db.ForeignKey('users.user_id'),
                            nullable=False, index=True)
    match_type = db.Column(db.Enum('roommate', 'room', name='match_type_enum'), nullable=False, index=True)
    match_id = db.Column(db.Integer, nullable=False)  # user_id or room_id
    
    # Score & Explanation
    match_score = db.Column(db.Numeric(5, 2), nullable=False)
    explanation = db.Column(db.Text)  # Human-readable explanation
    conflict_warnings = db.Column(db.JSON)  # Soft conflicts (non-blocking)
    
    # User Interaction
    viewed_at = db.Column(db.DateTime)  # When user viewed this
    liked = db.Column(db.Boolean)  # True=liked, False=disliked, None=not rated
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        match_type_str = self.match_type if self.match_type else 'unknown'
        return f'<Recommendation {self.recommendation_id}: {match_type_str}#{self.match_id} ({self.match_score}/100)>'
    
    def to_dict(self, include_explanation=True):
        """
        Convert recommendation to dictionary
        
        Args:
            include_explanation: Whether to include detailed explanation
        
        Returns:
            dict: Recommendation data
        """
        data = {
            'recommendation_id': self.recommendation_id,
            'match_type': self.match_type,
            'match_id': self.match_id,
            'match_score': float(self.match_score),
            'conflict_warnings': self.conflict_warnings,
            'viewed_at': self.viewed_at.isoformat() if self.viewed_at else None,
            'liked': self.liked,
            'created_at': self.created_at.isoformat(),
        }
        
        if include_explanation:
            data['explanation'] = self.explanation
        
        return data
    
    def mark_viewed(self):
        """
        Record that user viewed this recommendation
        
        Returns:
            True if successful
        
        Example:
            recommendation.mark_viewed()
            db.session.commit()
        """
        if not self.viewed_at:
            self.viewed_at = datetime.utcnow()
            return True
        return False
    
    def is_viewed(self):
        """Check if user has viewed this recommendation"""
        return self.viewed_at is not None
    
    def mark_liked(self):
        """
        Record that user liked this match
        
        Returns:
            None
        """
        self.liked = True
    
    def mark_disliked(self):
        """Record that user explicitly disliked"""
        self.liked = False
    
    def get_interaction_status(self):
        """
        Get user's interaction status with this recommendation
        
        Returns:
            str: 'new', 'viewed', 'liked', or 'disliked'
        """
        if self.liked is True:
            return 'liked'
        elif self.liked is False:
            return 'disliked'
        elif self.viewed_at:
            return 'viewed'
        else:
            return 'new'
    
    def has_warnings(self):
        """Check if there are conflict warnings"""
        return self.conflict_warnings is not None and len(self.conflict_warnings) > 0
    
    def get_warnings_text(self):
        """
        Get human-readable warning text
        
        Returns:
            str: Warnings description, or empty string if none
        """
        if not self.conflict_warnings:
            return ""
        
        warnings = []
        for warning in self.conflict_warnings:
            if isinstance(warning, dict):
                desc = warning.get('description', '')
            else:
                desc = str(warning)
            warnings.append(f"⚠️  {desc}")
        
        return "\n".join(warnings)
    
    def get_compatibility_label(self):
        """
        Get human-readable compatibility label
        
        Returns:
            str: Label like "Excellent", "Good", "Fair", etc.
        """
        score = float(self.match_score)
        
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
            return "Low Match"
    
    @staticmethod
    def get_user_recommendations(user_id, match_type=None, liked_only=False):
        """
        Get all recommendations for a user
        
        Args:
            user_id: User to get recommendations for
            match_type: Filter by 'roommate' or 'room' (None = both)
            liked_only: Only return liked recommendations
        
        Returns:
            list: List of Recommendation objects
        
        Example:
            liked_matches = Recommendation.get_user_recommendations(
                user_id=123,
                match_type='roommate',
                liked_only=True
            )
        """
        query = Recommendation.query.filter_by(requester_id=user_id)
        
        if match_type:
            query = query.filter_by(match_type=match_type)
        
        if liked_only:
            query = query.filter_by(liked=True)
        
        return query.order_by(Recommendation.created_at.desc()).all()
    
    @staticmethod
    def get_recent_recommendations(user_id, limit=10):
        """
        Get most recent recommendations for a user
        
        Args:
            user_id: User ID
            limit: Maximum number to return
        
        Returns:
            list: Most recent recommendations
        """
        return Recommendation.query.filter_by(requester_id=user_id).order_by(
            Recommendation.created_at.desc()
        ).limit(limit).all()
    
    @staticmethod
    def get_new_recommendations(user_id, limit=10):
        """
        Get unviewed recommendations for a user
        
        Args:
            user_id: User ID
            limit: Maximum to return
        
        Returns:
            list: Unviewed recommendations
        """
        return Recommendation.query.filter_by(
            requester_id=user_id,
            viewed_at=None
        ).order_by(
            Recommendation.match_score.desc()
        ).limit(limit).all()
    
    @staticmethod
    def get_viewed_count(user_id):
        """Get count of viewed recommendations"""
        return Recommendation.query.filter(
            Recommendation.requester_id == user_id,
            Recommendation.viewed_at != None
        ).count()
    
    @staticmethod
    def get_like_rate(user_id):
        """
        Get user's like rate (likes / total interactions)
        
        Args:
            user_id: User ID
        
        Returns:
            float: Like rate (0-1), or None if no interactions
        """
        total = Recommendation.query.filter_by(requester_id=user_id).count()
        
        if total == 0:
            return None
        
        likes = Recommendation.query.filter(
            Recommendation.requester_id == user_id,
            Recommendation.liked == True
        ).count()
        
        return likes / total if total > 0 else 0
    
    @staticmethod
    def count_pending(user_id):
        """Count unviewed recommendations for user"""
        return Recommendation.query.filter(
            Recommendation.requester_id == user_id,
            Recommendation.viewed_at == None
        ).count()
