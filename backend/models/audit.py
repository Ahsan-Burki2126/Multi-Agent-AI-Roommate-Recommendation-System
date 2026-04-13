"""
Audit Log Model
Records all agent decisions for transparency and auditability.

This table is crucial for the "explainability" requirement -
we can trace back WHY the system made any decision.
"""

from datetime import datetime
from sqlalchemy import Integer, String, Text
from backend.database import db


class AuditLog(db.Model):
    """
    Log of all agent decisions and system actions
    
    Purpose: Ensure system transparency by recording
    - What agent made what decision
    - What entity was affected
    - What details were involved
    - When it happened
    
    This allows us to:
    - Trace any recommendation back to the agents that made it
    - Audit for fairness/bias
    - Debug issues
    - Demonstrate explainability to users
    
    Attributes:
        log_id: Unique identifier
        agent_name: Which agent made this decision
        action: What action was taken
        entity_type: What type of entity ('user', 'room', 'score', etc.)
        entity_id: ID of the entity affected
        details: JSON with decision details & reasoning
        timestamp: When this happened
    """
    
    __tablename__ = 'audit_log'
    
    # Primary Key
    log_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Agent & Action
    agent_name = db.Column(db.String(100), nullable=False, index=True)
    action = db.Column(db.String(255), nullable=False)
    
    # Entity
    entity_type = db.Column(db.String(50), index=True)  # 'user', 'room', 'score', etc.
    entity_id = db.Column(db.Integer, index=True)
    
    # Details (JSON as text)
    details = db.Column(db.Text)  # JSON-formatted details
    
    # Timestamp
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, 
                         nullable=False, index=True)
    
    def __repr__(self):
        return f'<AuditLog {self.action} on {self.entity_type}#{self.entity_id}>'
    
    def to_dict(self):
        """
        Convert audit entry to dictionary
        
        Returns:
            dict: Audit log entry
        """
        import json
        
        details_dict = {}
        if self.details:
            try:
                details_dict = json.loads(self.details)
            except:
                details_dict = {'raw': self.details}
        
        return {
            'log_id': self.log_id,
            'agent_name': self.agent_name,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'details': details_dict,
            'timestamp': self.timestamp.isoformat(),
        }
    
    @staticmethod
    def get_logs_for_entity(entity_type, entity_id):
        """
        Get all logs related to a specific entity
        
        Args:
            entity_type: Type like 'user', 'score', 'room'
            entity_id: Entity ID
        
        Returns:
            list: Audit logs in chronological order
        
        Example:
            # Get all decisions that affected user #5
            logs = AuditLog.get_logs_for_entity('user', 5)
            
            # Can see: created account, set preferences, computed vectors,
            #          generated scores, got recommendations, liked match, etc.
        """
        return AuditLog.query.filter_by(
            entity_type=entity_type,
            entity_id=entity_id
        ).order_by(AuditLog.timestamp.asc()).all()
    
    @staticmethod
    def get_logs_for_agent(agent_name, limit=100):
        """
        Get all logs for a specific agent
        
        Args:
            agent_name: Name of agent
            limit: Maximum to return
        
        Returns:
            list: Recent agent logs
        """
        return AuditLog.query.filter_by(
            agent_name=agent_name
        ).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    
    @staticmethod
    def get_logs_for_action(action, limit=50):
        """
        Get all logs for a specific action
        
        Args:
            action: Action name ('validated_input', 'computed_score', etc.)
            limit: Maximum to return
        
        Returns:
            list: Logs for this action
        """
        return AuditLog.query.filter_by(
            action=action
        ).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    
    @staticmethod
    def get_recommendation_trace(user_a_id, user_b_id):
        """
        Get complete trace of how a recommendation was made
        
        Shows all agent decisions leading to matching these users
        
        Args:
            user_a_id: User receiving recommendation
            user_b_id: User being recommended
        
        Returns:
            list: Audit logs in chronological order
        
        Example:
            trace = AuditLog.get_recommendation_trace(123, 456)
            # Shows:
            # - Profiling Agent: Validated user 123
            # - Analysis Agent: Vectorized user 123 & 456
            # - Scoring Agent: Computed similarity (0.85)
            # - Conflict Detection: Found no hard conflicts
            # - Recommendation Engine: Generated explanation
        """
        # Filter at the database level — do NOT load the entire table into memory
        return AuditLog.query.filter(
            AuditLog.entity_id.in_([user_a_id, user_b_id])
        ).order_by(AuditLog.timestamp.asc()).all()
    
    @staticmethod
    def get_agent_timeline(limit=100):
        """
        Get timeline of all agent decisions (most recent first)
        
        Args:
            limit: Maximum to return
        
        Returns:
            list: Recent logs
        """
        return AuditLog.query.order_by(
            AuditLog.timestamp.desc()
        ).limit(limit).all()
    
    @staticmethod
    def count_logs(agent_name=None, action=None, entity_type=None):
        """
        Count logs matching criteria
        
        Args:
            agent_name: Filter by agent (optional)
            action: Filter by action (optional)
            entity_type: Filter by entity type (optional)
        
        Returns:
            int: Count of matching logs
        """
        query = AuditLog.query
        
        if agent_name:
            query = query.filter_by(agent_name=agent_name)
        if action:
            query = query.filter_by(action=action)
        if entity_type:
            query = query.filter_by(entity_type=entity_type)
        
        return query.count()
    
    @staticmethod
    def get_agent_activity(agent_name, hours=24):
        """
        Get recent activity for a specific agent
        
        Args:
            agent_name: Agent name
            hours: Look back this many hours
        
        Returns:
            int: Number of actions in period
        """
        from datetime import timedelta
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        return AuditLog.query.filter(
            AuditLog.agent_name == agent_name,
            AuditLog.timestamp >= cutoff
        ).count()
    
    @staticmethod
    def cleanup_old_logs(days=90):
        """
        Delete logs older than threshold
        
        Args:
            days: Delete logs older than this many days
        
        Returns:
            int: Number of logs deleted
        """
        from datetime import timedelta
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        deleted = AuditLog.query.filter(
            AuditLog.timestamp < cutoff
        ).delete()
        
        db.session.commit()
        return deleted
