"""
Room Model
Represents an available room posting.

Room owners post rooms that users can search and match against
their preferences.
"""

from datetime import datetime
from sqlalchemy import Integer, String, Text, Date, Boolean, Numeric, JSON
from sqlalchemy.orm import relationship
from backend.database import db


class Room(db.Model):
    """
    Room listing posted by property owners
    
    A room is available for rent and can be:
    - Searched by users looking for housing
    - Matched against user preferences
    - Scored for compatibility with user
    
    Attributes:
        room_id: Unique identifier
        owner_id: User (property owner) who posted the room
        title: Room listing title
        description: Detailed description
        location: City/area where room is located
        rent_price: Monthly rent price
        room_type: Single/Shared/Master bedroom
        bedrooms: Number of bedrooms
        bathrooms: Number of bathrooms
        amenities: List of room features (WiFi, AC, etc.)
        smoking_allowed: Whether smoking is permitted
        pets_allowed: Whether pets are allowed
        images: URLs to room photos
        is_available: Whether room is currently available
        available_from: Date room becomes available
        lease_duration_months: Typical lease length
    """
    
    __tablename__ = 'rooms'
    
    # Primary Key & Foreign Key
    room_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), 
                        nullable=False, index=True)
    
    # Listing Info
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(200), nullable=False, index=True)
    
    # Rental Details
    rent_price = db.Column(db.Numeric(8, 2), nullable=False)
    room_type = db.Column(db.Enum('Single', 'Shared', 'Master', name='room_type_enum'),
                         nullable=False, index=True)
    bedrooms = db.Column(db.Integer)
    bathrooms = db.Column(db.Numeric(3, 1))
    
    # Features (JSON array)
    # Example: ["WiFi", "AC", "Kitchen access", "Balcony", "Furnished"]
    amenities = db.Column(db.JSON)
    
    # Rules
    smoking_allowed = db.Column(db.Boolean, default=False)
    pets_allowed = db.Column(db.Boolean, default=False)
    
    # Media (JSON array of URLs)
    # Example: ["http://example.com/room1.jpg", "http://example.com/room2.jpg"]
    images = db.Column(db.JSON)
    
    # Availability
    is_available = db.Column(db.Boolean, default=True, index=True)
    available_from = db.Column(db.Date)
    lease_duration_months = db.Column(db.Integer)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                          onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    owner = relationship('User', back_populates='rooms')
    
    def __repr__(self):
        return f'<Room {self.room_id}: {self.title}>'
    
    def to_dict(self, include_owner=False):
        """
        Convert room to dictionary
        
        Args:
            include_owner: Whether to include owner information
        
        Returns:
            dict: Room data
        """
        data = {
            'room_id': self.room_id,
            'title': self.title,
            'description': self.description,
            'location': self.location,
            'rent_price': float(self.rent_price),
            'room_type': self.room_type,
            'bedrooms': self.bedrooms,
            'bathrooms': float(self.bathrooms) if self.bathrooms else None,
            'amenities': self.amenities,
            'smoking_allowed': self.smoking_allowed,
            'pets_allowed': self.pets_allowed,
            'images': self.images,
            'is_available': self.is_available,
            'available_from': self.available_from.isoformat() if self.available_from else None,
            'lease_duration_months': self.lease_duration_months,
            'created_at': self.created_at.isoformat(),
            'owner_id': self.owner_id,
        }
        
        if include_owner and self.owner:
            data['owner'] = {
                'user_id': self.owner.user_id,
                'full_name': self.owner.full_name,
                'profile_picture': self.owner.profile_picture,
                'phone': self.owner.phone,
            }
        
        return data
    
    def to_search_result(self, match_score=None):
        """
        Return room formatted for search results
        
        Args:
            match_score: Compatibility score (0-100) if available
        
        Returns:
            dict: Simplified room data for search results
        """
        return {
            'room_id': self.room_id,
            'title': self.title,
            'location': self.location,
            'rent_price': float(self.rent_price),
            'room_type': self.room_type,
            'bedrooms': self.bedrooms,
            'bathrooms': float(self.bathrooms) if self.bathrooms else None,
            'image': self.images[0] if self.images else None,
            'match_score': match_score,
            'amenities': self.amenities[:3] if self.amenities else [],  # Top 3
        }
    
    def validate(self):
        """
        Validate room data
        
        Returns:
            tuple: (is_valid: bool, errors: list)
        """
        errors = []
        
        if not self.title or len(self.title.strip()) == 0:
            errors.append('Room title is required')
        
        if not self.location or len(self.location.strip()) == 0:
            errors.append('Location is required')
        
        if not self.rent_price or float(self.rent_price) <= 0:
            errors.append('Rent price must be positive')
        
        if not self.room_type:
            errors.append('Room type is required')
        
        if not self.images or len(self.images) == 0:
            errors.append('At least one image is required')
        
        return len(errors) == 0, errors
    
    def matches_budget(self, budget_min, budget_max):
        """
        Check if room price falls within user's budget
        
        Args:
            budget_min: User's minimum budget
            budget_max: User's maximum budget
        
        Returns:
            bool: True if price is within range
        """
        price = float(self.rent_price)
        return budget_min <= price <= budget_max
    
    def matches_location(self, preferred_location):
        """
        Check if room location matches user preference
        
        Args:
            preferred_location: User's preferred city/area
        
        Returns:
            bool: True if location matches
        """
        if not preferred_location:
            return True  # No location preference = matches all
        
        return self.location.lower() == preferred_location.lower()
    
    def matches_room_type(self, preferred_type):
        """
        Check if room type matches user preference
        
        Args:
            preferred_type: Preferred room type (Single/Shared/Any)
        
        Returns:
            bool: True if type matches
        """
        if preferred_type == 'Any' or not preferred_type:
            return True
        
        return self.room_type == preferred_type
    
    def has_amenity(self, amenity_name):
        """
        Check if room has a specific amenity
        
        Args:
            amenity_name: Name of amenity to check
        
        Returns:
            bool: True if room has amenity
        
        Example:
            if room.has_amenity('WiFi'):
                # Room has WiFi
        """
        if not self.amenities:
            return False
        return amenity_name.lower() in [a.lower() for a in self.amenities]
    
    def matches_constraints(self, preferences):
        """
        Check if room matches all hard constraints
        
        Args:
            preferences: UserPreference object or dict
        
        Returns:
            tuple: (matches: bool, blocking_reasons: list)
        
        Example:
            matches, reasons = room.matches_constraints(user_prefs)
            if not matches:
                print(f"Room doesn't match: {reasons}")
        """
        blocking_reasons = []
        
        # Convert dict preferences to object if needed
        if isinstance(preferences, dict):
            pref_dict = preferences
        else:
            pref_dict = preferences.to_dict()
        
        # Check hard constraints
        if not self.pets_allowed and pref_dict.get('pets_ok', False):
            blocking_reasons.append('Room does not allow pets')
        
        if not self.smoking_allowed and pref_dict.get('smoking_ok', False):
            blocking_reasons.append('Room does not allow smoking')
        
        # Check budget
        if not self.matches_budget(
            float(pref_dict.get('budget_min', 0)),
            float(pref_dict.get('budget_max', 10000))
        ):
            blocking_reasons.append('Room is outside budget range')
        
        # Check location
        if not self.matches_location(pref_dict.get('preferred_location')):
            blocking_reasons.append('Room location does not match preference')
        
        return len(blocking_reasons) == 0, blocking_reasons
    
    def get_compatibility_score(self, preferences):
        """
        Compute how well room matches user preferences (0-100)
        
        Used by Room Matching Agent
        
        Args:
            preferences: UserPreference object or dict
        
        Returns:
            int: Compatibility score (0-100)
        """
        if isinstance(preferences, dict):
            pref_dict = preferences
        else:
            pref_dict = preferences.to_dict()
        
        # Check hard constraints first
        matches, _ = self.matches_constraints(preferences)
        if not matches:
            return 0  # Hard constraint violation = no match
        
        score = 0
        
        # Budget match (40 points max)
        if self.matches_budget(
            float(pref_dict.get('budget_min', 0)),
            float(pref_dict.get('budget_max', 10000))
        ):
            score += 40
        
        # Location match (30 points max)
        if self.matches_location(pref_dict.get('preferred_location')):
            score += 30
        
        # Room type match (20 points max)
        if self.matches_room_type(pref_dict.get('preferred_room_type', 'Any')):
            score += 20
        
        # Amenities match (10 points max)
        # Give points if room has amenities
        basic_amenities = ['WiFi', 'AC', 'Furnished']
        amenity_points = 0
        for amenity in basic_amenities:
            if self.has_amenity(amenity):
                amenity_points += 3.3
        score += min(10, amenity_points)
        
        return int(min(100, max(0, score)))
    
    def is_expired(self):
        """
        Check if room's availability has passed
        
        Returns:
            bool: True if available_from date is in the past
        """
        if not self.available_from:
            return False
        
        from datetime import date
        return self.available_from < date.today()
