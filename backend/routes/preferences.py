"""
Preferences Routes
Handles user preference management and preference vectorization.

Endpoints:
- GET /preferences/user/<user_id> - Get user preferences
- POST /preferences/user/<user_id> - Create/update user preferences
- PUT /preferences/user/<user_id> - Update preferences
- GET /preferences/<user_id>/vector - Get preference vector
- POST /preferences/<user_id>/vectorize - Compute preference vector (Analysis Agent)
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from backend.database import db
from backend.models import UserPreference, PreferenceVector, AuditLog
import json
import numpy as np
from decimal import Decimal

preferences_bp = Blueprint('preferences', __name__)


@preferences_bp.route('/user/<int:user_id>', methods=['GET'])
@jwt_required()
def get_preferences(user_id):
    """
    Get user preferences
    
    Returns:
    {
        "preference_id": 1,
        "user_id": 5,
        "budget_min": 800.00,
        "budget_max": 1200.00,
        "preferred_location": "San Francisco",
        "gender_preference": "Any",
        "age_min": 22,
        "age_max": 30,
        "cleanliness_level": "Clean",
        "schedule": "9-5 Job",
        "smoking_ok": false,
        "pets_ok": true,
        "noise_tolerance": 7,
        "preferred_room_type": "Shared",
        "lease_duration_months": 12
    }
    """
    try:
        current_user = int(get_jwt_identity())
        
        # Users can only view their own preferences
        if current_user != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        prefs = UserPreference.query.filter_by(user_id=user_id).first()
        if not prefs:
            return jsonify({'error': 'No preferences found'}), 404
        
        return jsonify(prefs.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@preferences_bp.route('/user/<int:user_id>', methods=['POST'])
@jwt_required()
def create_preferences(user_id):
    """
    Create user preferences
    
    Request JSON:
    {
        "budget_min": 800,
        "budget_max": 1200,
        "preferred_location": "San Francisco",
        "gender_preference": "Any",
        "age_min": 22,
        "age_max": 30,
        "cleanliness_level": "Clean",
        "schedule": "9-5 Job",
        "smoking_ok": false,
        "pets_ok": true,
        "noise_tolerance": 7,
        "preferred_room_type": "Shared",
        "lease_duration_months": 12
    }
    
    Returns: Created preference object
    """
    try:
        current_user = int(get_jwt_identity())
        
        if current_user != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Check if preferences already exist
        existing = UserPreference.query.filter_by(user_id=user_id).first()
        if existing:
            return jsonify({'error': 'User already has preferences. Use PUT to update.'}), 409
        
        data = request.get_json()
        
        # Create preferences
        prefs = UserPreference(
            user_id=user_id,
            budget_min=Decimal(str(data.get('budget_min', 0))),
            budget_max=Decimal(str(data.get('budget_max', 10000))),
            preferred_location=data.get('preferred_location'),
            gender_preference=data.get('gender_preference', 'Any'),
            age_min=data.get('age_min'),
            age_max=data.get('age_max'),
            cleanliness_level=data.get('cleanliness_level'),
            schedule=data.get('schedule'),
            smoking_ok=data.get('smoking_ok', False),
            pets_ok=data.get('pets_ok', False),
            noise_tolerance=data.get('noise_tolerance'),
            preferred_room_type=data.get('preferred_room_type', 'Any'),
            lease_duration_months=data.get('lease_duration_months')
        )
        
        # Validate
        is_valid, errors = prefs.validate()
        if not is_valid:
            return jsonify({'error': 'Validation failed', 'details': errors}), 400
        
        db.session.add(prefs)
        db.session.commit()
        
        # Log creation
        audit = AuditLog(
            agent_name='Profiling Agent',
            action='preferences_created',
            entity_type='user',
            entity_id=user_id,
            details=json.dumps({
                'budget_range': f"${prefs.budget_min}-${prefs.budget_max}",
                'location': prefs.preferred_location,
                'constraints': {
                    'smoking_ok': prefs.smoking_ok,
                    'pets_ok': prefs.pets_ok
                }
            }),
            timestamp=datetime.utcnow()
        )
        db.session.add(audit)
        db.session.commit()
        
        return jsonify(prefs.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@preferences_bp.route('/user/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_preferences(user_id):
    """
    Update user preferences
    
    Same JSON structure as POST
    Returns: Updated preference object
    """
    try:
        current_user = int(get_jwt_identity())
        
        if current_user != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        prefs = UserPreference.query.filter_by(user_id=user_id).first()
        if not prefs:
            return jsonify({'error': 'Preferences not found'}), 404
        
        data = request.get_json()
        
        # Update fields
        if 'budget_min' in data:
            prefs.budget_min = Decimal(str(data['budget_min']))
        if 'budget_max' in data:
            prefs.budget_max = Decimal(str(data['budget_max']))
        if 'preferred_location' in data:
            prefs.preferred_location = data['preferred_location']
        if 'gender_preference' in data:
            prefs.gender_preference = data['gender_preference']
        if 'age_min' in data:
            prefs.age_min = data['age_min']
        if 'age_max' in data:
            prefs.age_max = data['age_max']
        if 'cleanliness_level' in data:
            prefs.cleanliness_level = data['cleanliness_level']
        if 'schedule' in data:
            prefs.schedule = data['schedule']
        if 'smoking_ok' in data:
            prefs.smoking_ok = data['smoking_ok']
        if 'pets_ok' in data:
            prefs.pets_ok = data['pets_ok']
        if 'noise_tolerance' in data:
            prefs.noise_tolerance = data['noise_tolerance']
        if 'preferred_room_type' in data:
            prefs.preferred_room_type = data['preferred_room_type']
        if 'lease_duration_months' in data:
            prefs.lease_duration_months = data['lease_duration_months']
        
        # Invalidate preference vector (will need recomputation)
        existing_vector = PreferenceVector.query.filter_by(user_id=user_id).first()
        if existing_vector:
            db.session.delete(existing_vector)
        
        # Validate
        is_valid, errors = prefs.validate()
        if not is_valid:
            return jsonify({'error': 'Validation failed', 'details': errors}), 400
        
        db.session.commit()
        
        # Log update
        audit = AuditLog(
            agent_name='Profiling Agent',
            action='preferences_updated',
            entity_type='user',
            entity_id=user_id,
            details=json.dumps({
                'updated_fields': list(data.keys())
            }),
            timestamp=datetime.utcnow()
        )
        db.session.add(audit)
        db.session.commit()
        
        return jsonify(prefs.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@preferences_bp.route('/<int:user_id>/vector', methods=['GET'])
@jwt_required()
def get_preference_vector(user_id):
    """
    Get user's preference vector (if computed)
    
    Returns:
    {
        "vector_id": 1,
        "user_id": 5,
        "vector_data": [0.8, 0.7, 0.9, ...],
        "vector_norm": 1.42,
        "computed_at": "2026-02-24T10:00:00",
        "is_stale": false
    }
    """
    try:
        current_user = int(get_jwt_identity())
        
        if current_user != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        vector = PreferenceVector.query.filter_by(user_id=user_id).first()
        if not vector:
            return jsonify({'error': 'Vector not computed yet. Call /vectorize endpoint.'}), 404
        
        return jsonify({
            'vector_id': vector.vector_id,
            'user_id': vector.user_id,
            'vector_data': vector.vector_data,
            'vector_norm': float(vector.vector_norm) if vector.vector_norm else None,
            'computed_at': vector.computed_at.isoformat() if vector.computed_at else None,
            'is_stale': vector.is_stale()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@preferences_bp.route('/<int:user_id>/vectorize', methods=['POST'])
@jwt_required()
def vectorize_preferences(user_id):
    """
    Vectorize user preferences (Analysis Agent action)
    
    This converts raw preferences into a mathematical vector
    for similarity computation with other users.
    
    Returns:
    {
        "vector_id": 1,
        "user_id": 5,
        "vector_data": [0.8, 0.7, 0.9, ...],
        "vector_norm": 1.42,
        "message": "Vector computed successfully"
    }
    """
    try:
        current_user = int(get_jwt_identity())
        
        if current_user != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Get user preferences
        prefs = UserPreference.query.filter_by(user_id=user_id).first()
        if not prefs:
            return jsonify({'error': 'User preferences not found. Create preferences first.'}), 404
        
        # Convert preferences to vector (simple example)
        # Real implementation would use more sophisticated feature engineering
        vector_data = [
            float(prefs.budget_min) / 2000.0,  # Normalize budget min
            float(prefs.budget_max) / 3000.0,  # Normalize budget max
            (prefs.age_min or 20) / 60.0 if prefs.age_min else 0.33,  # Normalize age
            (prefs.noise_tolerance or 5) / 10.0,  # Normalize noise tolerance (0-1)
            1.0 if prefs.smoking_ok else 0.0,  # Smoking preference
            1.0 if prefs.pets_ok else 0.0,  # Pets preference
        ]
        
        # Compute norm
        vector_norm = float(np.linalg.norm(vector_data))
        
        # Delete existing vector
        existing = PreferenceVector.query.filter_by(user_id=user_id).first()
        if existing:
            db.session.delete(existing)
        
        # Create new vector
        vector = PreferenceVector(
            user_id=user_id,
            vector_data=vector_data,
            vector_norm=vector_norm,
            preference_weights={
                'cosine_similarity': 0.3,
                'lifestyle_match': 0.2,
                'schedule_compatibility': 0.2,
                'budget_alignment': 0.15,
                'habits_alignment': 0.15
            },
            computed_at=datetime.utcnow()
        )
        
        db.session.add(vector)
        db.session.commit()
        
        # Log vectorization
        audit = AuditLog(
            agent_name='Analysis Agent',
            action='computed_vector',
            entity_type='user',
            entity_id=user_id,
            details=json.dumps({
                'vector_dim': len(vector_data),
                'vector_norm': float(vector_norm),
                'components': [
                    'budget_min',
                    'budget_max',
                    'age_min',
                    'noise_tolerance',
                    'smoking_ok',
                    'pets_ok'
                ]
            }),
            timestamp=datetime.utcnow()
        )
        db.session.add(audit)
        db.session.commit()
        
        return jsonify({
            'vector_id': vector.vector_id,
            'user_id': vector.user_id,
            'vector_data': vector.vector_data,
            'vector_norm': float(vector.vector_norm),
            'message': 'Vector computed successfully'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
