"""
User Model
Represents a user account in the system.
Each user can be a roommate seeker AND/OR a room owner.
"""

from datetime import datetime
from sqlalchemy import Boolean, String, Text, DateTime
from sqlalchemy.orm import relationship
import bcrypt
from backend.database import db


class User(db.Model):
    """
    User account model
    
    A user can:
    - Seek roommates (has preferences, gets recommendations)
    - Post rooms for rent (is room owner)
    - Like/unlike potential matches
    - Message with matches
    
    Attributes:
        user_id: Unique identifier (auto-increment)
        email: User's email (unique, used for login)
        password_hash: Bcrypt hashed password
        full_name: User's full name
        gender: Gender (M/F/Other)
        city: City where user is located/seeking
        phone: Contact phone number
        profile_picture: URL to profile photo
        bio: User's bio/description
        is_active: Whether account is active
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """
    
    __tablename__ = 'users'
    
    # Primary Key
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Authentication
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Basic Info
    full_name = db.Column(db.String(255), nullable=False)
    gender = db.Column(db.Enum('M', 'F', 'Other'), nullable=True)
    city = db.Column(db.String(100), index=True)
    phone = db.Column(db.String(20))
    
    # Profile
    profile_picture = db.Column(db.String(500))  # URL to image
    bio = db.Column(db.Text)
    
    # Status
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, 
                          onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    preferences = relationship('UserPreference', back_populates='user', 
                              cascade='all, delete-orphan', uselist=False)
    rooms = relationship('Room', back_populates='owner', cascade='all, delete-orphan')
    
    # Recommendations made FOR this user (where this user is the requester)
    recommendations_requested = relationship(
        'Recommendation',
        foreign_keys='Recommendation.requester_id',
        backref='requester',
        cascade='all, delete-orphan'
    )
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    def set_password(self, password):
        """
        Hash password with bcrypt and store hash
        
        Args:
            password: Plain text password
        
        Returns:
            None
        
        Example:
            user.set_password('SecurePass123!')
            db.session.commit()
        """
        if not password or len(password) < 8:
            raise ValueError('Password must be at least 8 characters')
        
        # Hash with bcrypt (10 salt rounds as per config)
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt(rounds=10)
        ).decode('utf-8')
    
    def check_password(self, password):
        """
        Verify password against stored hash
        
        Args:
            password: Plain text password to verify
        
        Returns:
            bool: True if password matches, False otherwise
        
        Example:
            if user.check_password(provided_password):
                # Login successful
        """
        if not password or not self.password_hash:
            return False
        
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                self.password_hash.encode('utf-8')
            )
        except Exception:
            return False
    
    def to_dict(self, include_private=False):
        """
        Convert user to dictionary for JSON response
        
        Args:
            include_private: Whether to include non-public fields
        
        Returns:
            dict: User data
        
        Example:
            user_json = user.to_dict()
            return jsonify(user_json)
        """
        data = {
            'user_id': self.user_id,
            'email': self.email,
            'full_name': self.full_name,
            'gender': self.gender,
            'city': self.city,
            'profile_picture': self.profile_picture,
            'bio': self.bio,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_private:
            data['phone'] = self.phone
            data['is_active'] = self.is_active
            data['updated_at'] = self.updated_at.isoformat()
        
        return data
    
    def to_profile_dict(self):
        """
        Return complete profile (for owner viewing their own)
        
        Returns:
            dict: Full profile data
        """
        return {
            'user_id': self.user_id,
            'email': self.email,
            'full_name': self.full_name,
            'gender': self.gender,
            'city': self.city,
            'phone': self.phone,
            'profile_picture': self.profile_picture,
            'bio': self.bio,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
    
    @staticmethod
    def get_by_email(email):
        """
        Lookup user by email (for login)
        
        Args:
            email: Email address
        
        Returns:
            User object if found, None otherwise
        
        Example:
            user = User.get_by_email('alice@example.com')
            if user and user.check_password(password):
                # Login successful
        """
        return User.query.filter_by(email=email.lower()).first()
    
    @staticmethod
    def get_by_id(user_id):
        """
        Lookup user by ID
        
        Args:
            user_id: User ID
        
        Returns:
            User object if found, None otherwise
        """
        return User.query.get(user_id)
    
    def validate(self):
        """
        Validate user data before save
        
        Returns:
            tuple: (is_valid: bool, errors: list)
        
        Raises:
            ValueError: If validation fails
        """
        errors = []
        
        if not self.email:
            errors.append('Email is required')
        elif '@' not in self.email:
            errors.append('Invalid email format')
        
        if not self.full_name or len(self.full_name.strip()) == 0:
            errors.append('Full name is required')
        
        if not self.password_hash:
            errors.append('Password hash is required')
        
        if self.gender and self.gender not in ['M', 'F', 'Other']:
            errors.append('Invalid gender value')
        
        return len(errors) == 0, errors
    
    def is_complete_profile(self):
        """
        Check if user has filled out complete profile
        
        Returns:
            bool: True if city, bio, photo are set
        """
        return bool(self.city and self.bio and self.profile_picture)
    
    def has_preferences(self):
        """Check if user has set roommate preferences"""
        return self.preferences is not None
    
    def has_rooms(self):
        """Check if user has posted any rooms"""
        return len(self.rooms) > 0
