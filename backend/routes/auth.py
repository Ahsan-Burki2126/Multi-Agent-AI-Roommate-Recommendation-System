"""
Authentication Routes
Handles user registration, login, and token management.

Endpoints:
- POST /auth/register - Register new user
- POST /auth/login - Login user and get JWT token
- POST /auth/refresh - Refresh JWT token
- POST /auth/logout - Logout user
- GET /auth/verify - Verify if user is authenticated
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from backend.database import db
from backend.models import User, AuditLog
import json
import re

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user account
    
    Request JSON:
    {
        "email": "user@example.com",
        "password": "SecurePass123!",
        "full_name": "John Doe",
        "phone": "+1234567890",
        "gender": "M",
        "city": "San Francisco"
    }
    
    Returns:
    {
        "user_id": 1,
        "email": "user@example.com",
        "full_name": "John Doe",
        "message": "Registration successful"
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'password', 'full_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing field: {field}'}), 400
        
        # Check if email already exists
        if User.query.filter_by(email=data['email'].lower()).first():
            return jsonify({'error': 'Email already registered'}), 409
        
        # Map gender values from frontend to backend format
        gender_mapping = {
            'Male': 'M',
            'Female': 'F',
            'Other': 'Other',
            'Prefer not to say': None,
            'M': 'M',
            'F': 'F',
            '': None,
            None: None
        }
        gender_value = gender_mapping.get(data.get('gender'), None)
        
        # Create user
        user = User(
            email=data['email'].lower(),
            full_name=data['full_name'],
            phone=data.get('phone'),
            gender=gender_value,
            city=data.get('city'),
            is_active=True
        )
        user.set_password(data['password'])
        
        # Validate user
        is_valid, errors = user.validate()
        if not is_valid:
            return jsonify({'error': 'Validation failed', 'details': errors}), 400
        
        db.session.add(user)
        db.session.commit()
        
        # Log registration (Profiling Agent action)
        audit = AuditLog(
            agent_name='Profiling Agent',
            action='user_registered',
            entity_type='user',
            entity_id=user.user_id,
            details=json.dumps({
                'email': user.email,
                'full_name': user.full_name,
                'city': user.city
            }),
            timestamp=datetime.utcnow()
        )
        db.session.add(audit)
        db.session.commit()
        
        return jsonify({
            'user_id': user.user_id,
            'email': user.email,
            'full_name': user.full_name,
            'message': 'Registration successful'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticate user and return JWT token
    
    Request JSON:
    {
        "email": "user@example.com",
        "password": "SecurePass123!"
    }
    
    Returns:
    {
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "user_id": 1,
        "email": "user@example.com",
        "full_name": "John Doe",
        "expires_in": 2592000
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Missing email or password'}), 400
        
        # Find user
        user = User.query.filter_by(email=data['email'].lower()).first()
        if not user or not user.check_password(data['password']):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account is inactive'}), 403
        
        # Create JWT token (identity must be a string)
        access_token = create_access_token(
            identity=str(user.user_id),
            expires_delta=timedelta(days=30)
        )
        
        return jsonify({
            'access_token': access_token,
            'user_id': user.user_id,
            'email': user.email,
            'full_name': user.full_name,
            'expires_in': 2592000  # 30 days in seconds
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required()
def refresh_token():
    """
    Refresh JWT token using current token
    
    Headers:
    Authorization: Bearer <current_token>
    
    Returns:
    {
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "expires_in": 2592000
    }
    """
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user or not user.is_active:
            return jsonify({'error': 'User not found or inactive'}), 401
        
        # Create new token (identity must be a string)
        access_token = create_access_token(
            identity=str(user.user_id),
            expires_delta=timedelta(days=30)
        )
        
        return jsonify({
            'access_token': access_token,
            'expires_in': 2592000
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/verify', methods=['GET'])
@jwt_required()
def verify():
    """
    Verify if user is authenticated and get current user info
    
    Headers:
    Authorization: Bearer <token>
    
    Returns:
    {
        "user_id": 1,
        "email": "user@example.com",
        "full_name": "John Doe",
        "authenticated": true
    }
    """
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'user_id': user.user_id,
            'email': user.email,
            'full_name': user.full_name,
            'city': user.city,
            'authenticated': True
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 401


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logout user (invalidate token)
    
    Headers:
    Authorization: Bearer <token>
    
    Returns:
    {
        "message": "Logged out successfully"
    }
    """
    # In a real implementation, you'd add the token to a blacklist
    # For now, just return success since JWT will expire naturally
    return jsonify({'message': 'Logged out successfully'}), 200


@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """
    Change user password
    
    Headers:
    Authorization: Bearer <token>
    
    Request JSON:
    {
        "current_password": "oldPassword123",
        "new_password": "newPassword456"
    }
    
    Returns:
    {
        "message": "Password changed successfully"
    }
    """
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        if not data.get('current_password') or not data.get('new_password'):
            return jsonify({'error': 'Current password and new password are required'}), 400
        
        # Verify current password
        if not user.check_password(data['current_password']):
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Validate new password
        if len(data['new_password']) < 8:
            return jsonify({'error': 'New password must be at least 8 characters'}), 400
        
        # Set new password
        user.set_password(data['new_password'])
        db.session.commit()
        
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
