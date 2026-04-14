"""
Conflict Log Model
Records potential conflicts detected between users or between user and room.

Hard conflicts are deal-breakers (blocking).
Soft conflicts are warnings (non-blocking).
"""

from datetime import datetime
from sqlalchemy import Integer, String, Text, Enum, DateTime
from backend.database import db


class ConflictLog(db.Model):
    """
    Recorded conflict between users or user and room
    
    The Conflict Detection Agent analyzes compatibility
    and logs any potential issues here.
    
    Two types:
    - Hard: Must reject the match (pets, smoking, budget)
    - Soft: Warn user but allow if they want (schedule mismatch)
    
    Attributes:
        conflict_id: Unique identifier
        user_a_id: First user (if roommate conflict)
        user_b_id: Second user (if roommate conflict)
        room_id: Room (if room conflict)
        conflict_type: 'Hard' or 'Soft'
        description: What the conflict is
        severity: 1-10 scale (10 = most severe)
        auto_generated_at: When detected
    """
    
    __tablename__ = 'conflict_log'
    
    # Primary Key
    conflict_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Entities Involved (at least one pair filled)
    user_a_id = db.Column(db.Integer, db.ForeignKey('users.user_id'),
                         nullable=True, index=True)
    user_b_id = db.Column(db.Integer, db.ForeignKey('users.user_id'),
                         nullable=True, index=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.room_id'),
                       nullable=True, index=True)
    
    # Conflict Details
    conflict_type = db.Column(db.Enum('Hard', 'Soft', name='conflict_type_enum'), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.Integer)  # 1-10 scale
    
    # Metadata
    auto_generated_at = db.Column(db.DateTime, default=datetime.utcnow, 
                                 nullable=False, index=True)
    
    def __repr__(self):
        return f'<ConflictLog {self.conflict_id}: {self.conflict_type} - {self.description[:50]}>'
    
    def to_dict(self):
        """
        Convert conflict to dictionary
        
        Returns:
            dict: Conflict data
        """
        return {
            'conflict_id': self.conflict_id,
            'user_a_id': self.user_a_id,
            'user_b_id': self.user_b_id,
            'room_id': self.room_id,
            'conflict_type': self.conflict_type,
            'description': self.description,
            'severity': self.severity,
            'auto_generated_at': self.auto_generated_at.isoformat(),
        }
    
    def is_hard_conflict(self):
        """Check if this is a hard conflict (deal-breaker)"""
        return self.conflict_type == 'Hard'
    
    def is_soft_conflict(self):
        """Check if this is a soft conflict (warning only)"""
        return self.conflict_type == 'Soft'
    
    def get_severity_label(self):
        """
        Get human-readable severity label
        
        Returns:
            str: 'Critical', 'High', 'Medium', 'Low', or 'Minor'
        """
        if self.severity >= 9:
            return 'Critical'
        elif self.severity >= 7:
            return 'High'
        elif self.severity >= 5:
            return 'Medium'
        elif self.severity >= 3:
            return 'Low'
        else:
            return 'Minor'
    
    @staticmethod
    def get_conflicts_for_pair(user_a_id, user_b_id):
        """
        Get all conflicts between two users
        
        Args:
            user_a_id: First user
            user_b_id: Second user
        
        Returns:
            list: Conflict objects
        """
        conflicts = ConflictLog.query.filter(
            ((ConflictLog.user_a_id == user_a_id) & (ConflictLog.user_b_id == user_b_id)) |
            ((ConflictLog.user_a_id == user_b_id) & (ConflictLog.user_b_id == user_a_id))
        ).all()
        
        return conflicts
    
    @staticmethod
    def get_hard_conflicts_for_pair(user_a_id, user_b_id):
        """
        Get hard conflicts (blockers) between two users
        
        Args:
            user_a_id: First user
            user_b_id: Second user
        
        Returns:
            list: Hard conflict objects
        
        Example:
            hard_conflicts = ConflictLog.get_hard_conflicts_for_pair(1, 2)
            if hard_conflicts:
                # This pair has deal-breakers, don't recommend
        """
        hard_conflicts = []
        all_conflicts = ConflictLog.get_conflicts_for_pair(user_a_id, user_b_id)
        
        for conflict in all_conflicts:
            if conflict.is_hard_conflict():
                hard_conflicts.append(conflict)
        
        return hard_conflicts
    
    @staticmethod
    def get_soft_conflicts_for_pair(user_a_id, user_b_id):
        """
        Get soft conflicts (warnings) between two users
        
        Args:
            user_a_id: First user
            user_b_id: Second user
        
        Returns:
            list: Soft conflict objects
        """
        return [
            c for c in ConflictLog.get_conflicts_for_pair(user_a_id, user_b_id)
            if c.is_soft_conflict()
        ]
    
    @staticmethod
    def has_hard_conflicts(user_a_id, user_b_id):
        """
        Quick check: do these users have hard conflicts?
        
        Args:
            user_a_id: First user
            user_b_id: Second user
        
        Returns:
            bool: True if any hard conflicts exist
        """
        return len(ConflictLog.get_hard_conflicts_for_pair(user_a_id, user_b_id)) > 0
    
    @staticmethod
    def get_conflicts_for_room(room_id):
        """
        Get all conflicts for a room
        
        Args:
            room_id: Room ID
        
        Returns:
            list: Conflict objects
        """
        return ConflictLog.query.filter_by(room_id=room_id).all()
    
    @staticmethod
    def get_user_conflict_count(user_id, hard_only=False):
        """
        Get count of conflicts for a user
        
        Args:
            user_id: User ID
            hard_only: Only count hard conflicts
        
        Returns:
            int: Conflict count
        """
        query = ConflictLog.query.filter(
            (ConflictLog.user_a_id == user_id) | (ConflictLog.user_b_id == user_id)
        )
        
        if hard_only:
            query = query.filter_by(conflict_type='Hard')
        
        return query.count()
    
    @staticmethod
    def get_recent_conflicts(limit=20):
        """
        Get most recent conflicts logged
        
        Args:
            limit: Maximum to return
        
        Returns:
            list: Recent conflicts
        """
        return ConflictLog.query.order_by(
            ConflictLog.auto_generated_at.desc()
        ).limit(limit).all()
    
    @staticmethod
    def create_hard_conflict(entity_a_type, entity_a_id, entity_b_type, entity_b_id,
                           description, severity=10):
        """
        Helper to create a hard conflict record
        
        Args:
            entity_a_type: 'user' or 'room'
            entity_a_id: ID of entity A
            entity_b_type: 'user' or 'room'
            entity_b_id: ID of entity B
            description: What the conflict is
            severity: 1-10 scale (default 10 for hard)
        
        Returns:
            ConflictLog object
        
        Example:
            conflict = ConflictLog.create_hard_conflict(
                'user', 1,
                'user', 2,
                'User 1 has dog but User 2 forbids pets',
                severity=10
            )
            db.session.add(conflict)
            db.session.commit()
        """
        conflict = ConflictLog(
            user_a_id=entity_a_id if entity_a_type == 'user' else None,
            user_b_id=entity_b_id if entity_b_type == 'user' else None,
            room_id=entity_b_id if entity_b_type == 'room' else None,
            conflict_type='Hard',
            description=description,
            severity=severity
        )
        return conflict
    
    @staticmethod
    def create_soft_conflict(entity_a_type, entity_a_id, entity_b_type, entity_b_id,
                            description, severity=5):
        """
        Helper to create a soft conflict record (warning)
        
        Args:
            entity_a_type: 'user' or 'room'
            entity_a_id: ID of entity A
            entity_b_type: 'user' or 'room'
            entity_b_id: ID of entity B
            description: What might be an issue
            severity: 1-10 scale (default 5 for soft)
        
        Returns:
            ConflictLog object
        
        Example:
            conflict = ConflictLog.create_soft_conflict(
                'user', 1,
                'user', 2,
                'User 1 works 9-5, User 2 works night shift',
                severity=6
            )
        """
        conflict = ConflictLog(
            user_a_id=entity_a_id if entity_a_type == 'user' else None,
            user_b_id=entity_b_id if entity_b_type == 'user' else None,
            room_id=entity_b_id if entity_b_type == 'room' else None,
            conflict_type='Soft',
            description=description,
            severity=severity
        )
        return conflict
