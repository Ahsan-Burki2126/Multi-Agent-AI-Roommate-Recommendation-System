"""
Room Routes
Handles room listing management and room search.

Endpoints:
- GET /rooms - List all available rooms
- POST /rooms - Create new room listing
- GET /rooms/<room_id> - Get room details
- PUT /rooms/<room_id> - Update room listing
- DELETE /rooms/<room_id> - Delete room listing
- GET /rooms/search - Search rooms by criteria
- GET /rooms/user/<user_id> - Get user's room listings
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from backend.database import db
from backend.models import Room, User, AuditLog
import json

rooms_bp = Blueprint('rooms', __name__)


@rooms_bp.route('', methods=['GET'])
def list_rooms():
    """
    List all available rooms with pagination
    
    Query Parameters:
    - limit: Max results (default 20)
    - offset: Pagination offset (default 0)
    
    Returns:
    {
        "rooms": [...],
        "total": 150,
        "limit": 20,
        "offset": 0
    }
    """
    try:
        query = Room.query.filter_by(is_available=True)
        
        # Pagination
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = int(request.args.get('offset', 0))
        
        total = query.count()
        rooms = query.order_by(Room.created_at.desc()).limit(limit).offset(offset).all()
        
        return jsonify({
            'rooms': [r.to_dict() for r in rooms],
            'total': total,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rooms_bp.route('', methods=['POST'])
@jwt_required()
def create_room():
    """
    Create new room listing
    
    Request JSON:
    {
        "title": "Cozy Shared Room in Mission",
        "description": "Bright shared room with large window",
        "location": "San Francisco",
        "address": "123 Mission St, SF, CA 94103",
        "room_type": "Shared",
        "rent_price": 950,
        "amenities": ["WiFi", "AC", "Washing Machine"],
        "images": ["url1.jpg", "url2.jpg"],
        "pets_allowed": true,
        "smoking_allowed": false,
        "available_from": "2026-03-01"
    }
    
    Returns: Created room object
    """
    try:
        user_id = int(get_jwt_identity())  # Convert string identity back to int
        data = request.get_json()
        
        # Parse available_from date
        available_from = None
        if data.get('available_from'):
            available_from = datetime.fromisoformat(data['available_from'])
        
        # Create room
        room = Room(
            owner_id=user_id,
            title=data.get('title'),
            description=data.get('description'),
            location=data.get('location'),
            room_type=data.get('room_type', 'Shared'),
            rent_price=float(data.get('rent_price', 0)),
            amenities=data.get('amenities', []),
            images=data.get('images', []),
            pets_allowed=data.get('pets_allowed', False),
            smoking_allowed=data.get('smoking_allowed', False),
            is_available=True,
            available_from=available_from
        )
        
        # Validate
        is_valid, errors = room.validate()
        if not is_valid:
            return jsonify({'error': 'Validation failed', 'details': errors}), 400
        
        db.session.add(room)
        db.session.commit()
        
        # Log creation
        audit = AuditLog(
            agent_name='Room Matching Agent',
            action='room_posted',
            entity_type='room',
            entity_id=room.room_id,
            details=json.dumps({
                'owner_id': user_id,
                'location': room.location,
                'rent_price': float(room.rent_price),
                'room_type': room.room_type
            }),
            timestamp=datetime.utcnow()
        )
        db.session.add(audit)
        db.session.commit()
        
        return jsonify(room.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@rooms_bp.route('/<int:room_id>', methods=['GET'])
def get_room(room_id):
    """
    Get room details by ID
    
    Returns: Room object with all details including owner info
    """
    try:
        room = Room.query.get(room_id)
        if not room:
            return jsonify({'error': 'Room not found'}), 404
        
        return jsonify(room.to_dict(include_owner=True)), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rooms_bp.route('/<int:room_id>', methods=['PUT'])
@jwt_required()
def update_room(room_id):
    """
    Update room listing
    
    Only room owner can update
    
    Request JSON: Same as POST
    Returns: Updated room object
    """
    try:
        user_id = int(get_jwt_identity())
        room = Room.query.get(room_id)
        
        if not room:
            return jsonify({'error': 'Room not found'}), 404
        
        # Check ownership
        if room.owner_id != user_id:
            return jsonify({'error': 'Unauthorized - not room owner'}), 403
        
        data = request.get_json()
        
        # Update fields
        if 'title' in data:
            room.title = data['title']
        if 'description' in data:
            room.description = data['description']
        if 'location' in data:
            room.location = data['location']
        if 'address' in data:
            room.address = data['address']
        if 'room_type' in data:
            room.room_type = data['room_type']
        if 'rent_price' in data:
            room.rent_price = float(data['rent_price'])
        if 'amenities' in data:
            room.amenities = data['amenities']
        if 'images' in data:
            room.images = data['images']
        if 'pets_allowed' in data:
            room.pets_allowed = data['pets_allowed']
        if 'smoking_allowed' in data:
            room.smoking_allowed = data['smoking_allowed']
        if 'is_available' in data:
            room.is_available = data['is_available']
        if 'available_from' in data:
            room.available_from = datetime.fromisoformat(data['available_from'])
        
        room.updated_at = datetime.utcnow()
        
        # Validate
        is_valid, errors = room.validate()
        if not is_valid:
            return jsonify({'error': 'Validation failed', 'details': errors}), 400
        
        db.session.commit()
        
        # Log update
        audit = AuditLog(
            agent_name='Room Matching Agent',
            action='room_updated',
            entity_type='room',
            entity_id=room.room_id,
            details=json.dumps({'updated_fields': list(data.keys())}),
            timestamp=datetime.utcnow()
        )
        db.session.add(audit)
        db.session.commit()
        
        return jsonify(room.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@rooms_bp.route('/<int:room_id>', methods=['DELETE'])
@jwt_required()
def delete_room(room_id):
    """
    Delete room listing (soft delete)
    
    Only room owner can delete
    
    Returns:
    {
        "message": "Room deleted",
        "room_id": 5
    }
    """
    try:
        user_id = int(get_jwt_identity())
        room = Room.query.get(room_id)
        
        if not room:
            return jsonify({'error': 'Room not found'}), 404
        
        # Check ownership
        if room.owner_id != user_id:
            return jsonify({'error': 'Unauthorized - not room owner'}), 403
        
        room.is_available = False
        room.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Log deletion
        audit = AuditLog(
            agent_name='Room Matching Agent',
            action='room_deleted',
            entity_type='room',
            entity_id=room.room_id,
            details=json.dumps({'deleted_at': datetime.utcnow().isoformat()}),
            timestamp=datetime.utcnow()
        )
        db.session.add(audit)
        db.session.commit()
        
        return jsonify({
            'message': 'Room deleted',
            'room_id': room_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@rooms_bp.route('/search', methods=['GET'])
def search_rooms():
    """
    Search rooms by criteria
    
    Query Parameters:
    - location: Filter by location (city)
    - min_price: Minimum rent price
    - max_price: Maximum rent price
    - room_type: Filter by room type (Single/Shared/Master)
    - pets: Allow pets (true/false)
    - smoking: Allow smoking (true/false)
    - limit: Max results (default 20)
    - offset: Pagination offset (default 0)
    
    Returns: List of matching rooms with pagination
    """
    try:
        query = Room.query.filter_by(is_available=True)
        
        # Apply filters
        location = request.args.get('location')
        if location:
            query = query.filter(Room.location.ilike(f'%{location}%'))
        
        min_price = request.args.get('min_price')
        if min_price:
            query = query.filter(Room.rent_price >= float(min_price))
        
        max_price = request.args.get('max_price')
        if max_price:
            query = query.filter(Room.rent_price <= float(max_price))
        
        room_type = request.args.get('room_type')
        if room_type:
            query = query.filter_by(room_type=room_type)
        
        pets = request.args.get('pets')
        if pets:
            query = query.filter_by(pets_allowed=pets.lower() == 'true')
        
        smoking = request.args.get('smoking')
        if smoking:
            query = query.filter_by(smoking_allowed=smoking.lower() == 'true')
        
        # Pagination
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = int(request.args.get('offset', 0))
        
        total = query.count()
        rooms = query.order_by(Room.created_at.desc()).limit(limit).offset(offset).all()
        
        return jsonify({
            'rooms': [r.to_dict() for r in rooms],
            'total': total,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rooms_bp.route('/import-hostels', methods=['POST'])
@jwt_required()
def import_hostels():
    """
    Manually trigger a Google Places hostel import for a city.

    Request JSON:
    { "city": "Bahawalpur" }

    Returns:
    { "saved": 8, "city": "Bahawalpur" }
    """
    try:
        data = request.get_json() or {}
        city = (data.get('city') or '').strip()
        if not city:
            return jsonify({'error': 'city is required'}), 400

        from backend.services.hostel_search import fetch_and_save_hostels
        saved = fetch_and_save_hostels(city)

        return jsonify({'saved': saved, 'city': city}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rooms_bp.route('/user/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user_rooms(user_id):
    """
    Get all rooms posted by a specific user
    
    Query Parameters:
    - limit: Max results
    - offset: Pagination offset
    
    Returns: User's room listings
    """
    try:
        current_user = int(get_jwt_identity())
        
        # Users can only view their own rooms (or admin can view any)
        if current_user != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        query = Room.query.filter_by(owner_id=user_id)
        
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = int(request.args.get('offset', 0))
        
        total = query.count()
        rooms = query.order_by(Room.created_at.desc()).limit(limit).offset(offset).all()
        
        return jsonify({
            'rooms': [r.to_dict() for r in rooms],
            'total': total,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
