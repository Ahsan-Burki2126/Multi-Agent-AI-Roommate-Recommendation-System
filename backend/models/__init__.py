"""
Database Models Package

This package contains all SQLAlchemy ORM models:
- User: Account management
- UserPreference: Raw preference data
- PreferenceVector: Vectorized preferences for similarity
- Room: Room listings
- CompatibilityScore: Cached match scores
- Recommendation: Match recommendations & interactions
- ConflictLog: Conflict detection results
- AuditLog: Decision traceability

Import all models here for easy access and Flask registration.
"""

from .user import User
from .preference import UserPreference, PreferenceVector
from .room import Room
from .score import CompatibilityScore
from .match import Recommendation
from .conflict import ConflictLog
from .audit import AuditLog

__all__ = [
    'User',
    'UserPreference',
    'PreferenceVector',
    'Room',
    'CompatibilityScore',
    'Recommendation',
    'ConflictLog',
    'AuditLog',
]
