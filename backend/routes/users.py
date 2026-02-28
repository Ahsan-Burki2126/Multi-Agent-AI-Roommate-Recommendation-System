"""
User Routes
Handles user profile management.

Endpoints:
- GET /users/<user_id> - Get user profile
- PUT /users/<user_id> - Update user profile
- GET /users/search - Search users
- DELETE /users/<user_id> - Deactivate account
- GET /users/<user_id>/profile - Get complete profile with preferences
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from backend.database import db
from backend.models import User, UserPreference, AuditLog
import json

users_bp = Blueprint('users', __name__)


@users_bp.route('/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """
    Get user profile by ID
    
    Returns:
    {
        "user_id": 1,
        "email": "user@example.com",
        "full_name": "John Doe",
        "phone": "+1234567890",
        "gender": "M",
        "city": "San Francisco",
        "bio": "Looking for roommates",
        "created_at": "2026-02-24T10:00:00",
        "updated_at": "2026-02-24T10:00:00"
    }
    """
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify(user.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@users_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """
    Update user profile
    
    Request JSON:
    {
        "full_name": "John Doe",
        "phone": "+1234567890",
        "gender": "M",
        "city": "San Francisco",
        "bio": "Looking for roommates",
        "profile_picture": "https://..."
    }
    
    Returns updated user object
    """
    try:
        current_user = int(get_jwt_identity())
        
        # Users can only update their own profile
        if current_user != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        # Update allowed fields
        allowed_fields = ['full_name', 'phone', 'gender', 'city', 'bio', 'profile_picture']
        for field in allowed_fields:
            if field in data:
                setattr(user, field, data[field])
        
        user.updated_at = datetime.utcnow()
        
        # Validate
        is_valid, errors = user.validate()
        if not is_valid:
            return jsonify({'error': 'Validation failed', 'details': errors}), 400
        
        db.session.commit()
        
        # Log update
        audit = AuditLog(
            agent_name='Profiling Agent',
            action='user_profile_updated',
            entity_type='user',
            entity_id=user.user_id,
            details=json.dumps({
                'updated_fields': list(data.keys())
            }),
            timestamp=datetime.utcnow()
        )
        db.session.add(audit)
        db.session.commit()
        
        return jsonify(user.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@users_bp.route('/<int:user_id>/profile', methods=['GET'])
@jwt_required()
def get_user_profile(user_id):
    """
    Get complete user profile with preferences
    
    Returns:
    {
        "user": {
            "user_id": 1,
            "email": "user@example.com",
            ...
        },
        "preferences": {
            "preference_id": 1,
            "budget_min": 800,
            "budget_max": 1200,
            ...
        }
    }
    """
    try:
        current_user = int(get_jwt_identity())
        
        # Users can only view their own profile unless they're admin
        if current_user != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        preferences = UserPreference.query.filter_by(user_id=user_id).first()
        
        return jsonify({
            'user': user.to_dict(),
            'preferences': preferences.to_dict() if preferences else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@users_bp.route('/search', methods=['GET'])
def search_users():
    """
    Search for users by criteria
    
    Query Parameters:
    - city: Filter by city
    - gender: Filter by gender (M/F/Other)
    - limit: Max results (default 20)
    - offset: Pagination offset (default 0)
    
    Returns:
    {
        "users": [...],
        "total": 150,
        "limit": 20,
        "offset": 0
    }
    """
    try:
        query = User.query.filter_by(is_active=True)
        
        # Apply filters
        city = request.args.get('city')
        if city:
            query = query.filter_by(city=city)
        
        gender = request.args.get('gender')
        if gender:
            query = query.filter_by(gender=gender)
        
        # Pagination
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = int(request.args.get('offset', 0))
        
        total = query.count()
        users = query.limit(limit).offset(offset).all()
        
        return jsonify({
            'users': [u.to_dict() for u in users],
            'total': total,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@users_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """
    Deactivate user account (soft delete)
    
    Returns:
    {
        "message": "Account deactivated",
        "user_id": 1
    }
    """
    try:
        current_user = int(get_jwt_identity())
        
        # Users can only delete their own account
        if current_user != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user.is_active = False
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Log deletion
        audit = AuditLog(
            agent_name='Profiling Agent',
            action='user_deactivated',
            entity_type='user',
            entity_id=user.user_id,
            details=json.dumps({'deactivated_at': datetime.utcnow().isoformat()}),
            timestamp=datetime.utcnow()
        )
        db.session.add(audit)
        db.session.commit()
        
        return jsonify({
            'message': 'Account deactivated',
            'user_id': user_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
