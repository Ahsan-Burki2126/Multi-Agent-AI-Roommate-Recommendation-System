"""
Matching Routes
Handles matching pipeline execution and match scoring.

Endpoints:
- POST /matches/compute - Trigger matching algorithm (Scoring Agent)
- GET /matches/user/<user_id> - Get computed matches for user
- POST /matches/<user_id_1>/<user_id_2> - Score two users (Scoring Agent)
- DELETE /matches/<score_id> - Clear cached score
- GET /matches/conflicts/<user_id_1>/<user_id_2> - Check conflicts (Conflict Detection Agent)
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from backend.database import db
from backend.models import (
    User, UserPreference, PreferenceVector, CompatibilityScore, ConflictLog, AuditLog
)
import json
import numpy as np

matches_bp = Blueprint('matches', __name__)


@matches_bp.route('/compute', methods=['POST'])
@jwt_required()
def compute_matches():
    """
    Trigger matching algorithm for current user
    
    This endpoint:
    1. Gets user's preference vector
    2. Finds other users with vectors
    3. Computes compatibility scores
    4. Checks for conflicts
    5. Stores results in database
    
    Request JSON (optional):
    {
        "target_user_id": 5,  # Optional: compute match for specific user only
        "min_score_threshold": 60  # Optional: only compute if expected score > threshold
    }
    
    Returns:
    {
        "user_id": 123,
        "matches_found": 15,
        "high_score_matches": 8,
        "message": "Matching completed"
    }
    """
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json() or {}
        
        # Get user's preference vector
        user_vector = PreferenceVector.query.filter_by(user_id=user_id).first()
        if not user_vector:
            return jsonify({'error': 'User preferences not vectorized. Call /preferences/{user_id}/vectorize first.'}), 400
        
        matches_found = 0
        high_score_matches = 0
        
        # Get target user or all active users
        if 'target_user_id' in data:
            candidate_users = User.query.filter(
                User.user_id == data['target_user_id'],
                User.is_active == True
            ).all()
        else:
            candidate_users = User.query.filter(
                User.user_id != user_id,
                User.is_active == True
            ).all()
        
        # Score each candidate
        for candidate in candidate_users:
            # Get candidate's vector
            candidate_vector = PreferenceVector.query.filter_by(user_id=candidate.user_id).first()
            if not candidate_vector:
                continue  # Skip if candidate has no vector
            
            # Check for hard conflicts first
            if ConflictLog.has_hard_conflicts(user_id, candidate.user_id):
                continue  # Skip matches with hard conflicts
            
            # Compute cosine similarity
            try:
                similarity = user_vector.get_similarity_with(candidate_vector)
            except:
                similarity = 0
            
            # Check if score already exists
            existing_score = CompatibilityScore.query.filter(
                ((CompatibilityScore.user_a_id == user_id) & (CompatibilityScore.user_b_id == candidate.user_id)) |
                ((CompatibilityScore.user_a_id == candidate.user_id) & (CompatibilityScore.user_b_id == user_id))
            ).first()
            
            # Compute real sub-scores
            user_prefs = UserPreference.query.filter_by(user_id=user_id).first()
            cand_prefs = UserPreference.query.filter_by(user_id=candidate.user_id).first()
            
            CLEAN_MAP = {'Very Clean': 10, 'Clean': 7, 'Average': 5, 'Relaxed': 2}
            SCHED_COMPAT = {
                ('9-5 Job', '9-5 Job'): 95, ('Night Shift', 'Night Shift'): 95,
                ('Student', 'Student'): 90, ('Flexible', 'Flexible'): 85,
                ('9-5 Job', 'Student'): 70, ('Student', '9-5 Job'): 70,
                ('Flexible', '9-5 Job'): 75, ('9-5 Job', 'Flexible'): 75,
                ('Flexible', 'Student'): 75, ('Student', 'Flexible'): 75,
                ('Flexible', 'Night Shift'): 65, ('Night Shift', 'Flexible'): 65,
                ('9-5 Job', 'Night Shift'): 30, ('Night Shift', '9-5 Job'): 30,
                ('Student', 'Night Shift'): 45, ('Night Shift', 'Student'): 45,
            }
            
            # Lifestyle score
            lifestyle_score = 50
            if user_prefs and cand_prefs:
                user_obj = User.query.get(user_id)
                if user_obj and user_obj.city and candidate.city and user_obj.city.lower() == candidate.city.lower():
                    lifestyle_score += 20
                clean_a = CLEAN_MAP.get(user_prefs.cleanliness_level, 5)
                clean_b = CLEAN_MAP.get(cand_prefs.cleanliness_level, 5)
                clean_gap = abs(clean_a - clean_b)
                if clean_gap == 0: lifestyle_score += 20
                elif clean_gap <= 2: lifestyle_score += 15
                elif clean_gap <= 4: lifestyle_score += 8
                noise_gap = abs(int(user_prefs.noise_tolerance or 5) - int(cand_prefs.noise_tolerance or 5))
                if noise_gap <= 2: lifestyle_score += 10
                elif noise_gap <= 4: lifestyle_score += 5
            lifestyle_score = min(100, lifestyle_score)
            
            # Schedule score  
            schedule_score = 60
            if user_prefs and cand_prefs:
                sched_a = user_prefs.schedule or 'Flexible'
                sched_b = cand_prefs.schedule or 'Flexible'
                schedule_score = SCHED_COMPAT.get((sched_a, sched_b), 55)
            
            # Budget score
            budget_score = 50
            if user_prefs and cand_prefs:
                try:
                    a_min, a_max = float(user_prefs.budget_min or 300), float(user_prefs.budget_max or 1500)
                    b_min, b_max = float(cand_prefs.budget_min or 300), float(cand_prefs.budget_max or 1500)
                    overlap_min = max(a_min, b_min)
                    overlap_max = min(a_max, b_max)
                    if overlap_min > overlap_max:
                        budget_score = 20
                    else:
                        overlap_range = overlap_max - overlap_min
                        a_range = max(a_max - a_min, 1)
                        b_range = max(b_max - b_min, 1)
                        overlap_pct = min(overlap_range / a_range, overlap_range / b_range)
                        budget_score = min(100, int(40 + (overlap_pct * 60)))
                except:
                    pass
            
            # Habits score  
            habits_score = 50
            if user_prefs and cand_prefs:
                habits_score = 100
                if user_prefs.smoking_ok != cand_prefs.smoking_ok: habits_score -= 35
                if user_prefs.pets_ok != cand_prefs.pets_ok: habits_score -= 25
                clean_a = CLEAN_MAP.get(user_prefs.cleanliness_level, 5)
                clean_b = CLEAN_MAP.get(cand_prefs.cleanliness_level, 5)
                clean_gap = abs(clean_a - clean_b)
                if clean_gap >= 5: habits_score -= 20
                elif clean_gap >= 3: habits_score -= 10
                habits_score = max(0, habits_score)
            
            # Age match score
            age_match_score = 70
            if user_prefs and cand_prefs:
                try:
                    a_min_age = int(user_prefs.age_min or 18)
                    a_max_age = int(user_prefs.age_max or 65)
                    b_min_age = int(cand_prefs.age_min or 18)
                    b_max_age = int(cand_prefs.age_max or 65)
                    overlap_min_age = max(a_min_age, b_min_age)
                    overlap_max_age = min(a_max_age, b_max_age)
                    if overlap_min_age > overlap_max_age:
                        age_match_score = 20
                    else:
                        overlap_range = overlap_max_age - overlap_min_age
                        a_range = max(a_max_age - a_min_age, 1)
                        b_range = max(b_max_age - b_min_age, 1)
                        overlap_pct = min(overlap_range / a_range, overlap_range / b_range)
                        age_match_score = min(100, int(40 + (overlap_pct * 60)))
                except:
                    pass
            
            # Compute overall score
            overall_score = int(
                similarity * 100 * 0.3 +
                lifestyle_score * 0.2 +
                schedule_score * 0.2 +
                budget_score * 0.15 +
                habits_score * 0.15
            )
            
            if existing_score and not existing_score.is_stale():
                # Update existing score
                existing_score.overall_score = overall_score
                existing_score.lifestyle_score = lifestyle_score
                existing_score.schedule_score = schedule_score
                existing_score.budget_score = budget_score
                existing_score.habits_score = habits_score
                existing_score.age_match_score = age_match_score
                existing_score.computed_at = datetime.utcnow()
            else:
                # Create new score
                if existing_score:
                    db.session.delete(existing_score)
                
                score = CompatibilityScore(
                    user_a_id=user_id,
                    user_b_id=candidate.user_id,
                    overall_score=overall_score,
                    lifestyle_score=lifestyle_score,
                    schedule_score=schedule_score,
                    budget_score=budget_score,
                    habits_score=habits_score,
                    age_match_score=age_match_score,
                    computed_at=datetime.utcnow()
                )
                db.session.add(score)
            
            matches_found += 1
            if overall_score >= 70:
                high_score_matches += 1
        
        db.session.commit()
        
        # Log matching
        audit = AuditLog(
            agent_name='Scoring Agent',
            action='computed_matches',
            entity_type='user',
            entity_id=user_id,
            details=json.dumps({
                'matches_found': matches_found,
                'high_score_matches': high_score_matches,
                'timestamp': datetime.utcnow().isoformat()
            }),
            timestamp=datetime.utcnow()
        )
        db.session.add(audit)
        db.session.commit()
        
        return jsonify({
            'user_id': user_id,
            'matches_found': matches_found,
            'high_score_matches': high_score_matches,
            'message': 'Matching completed'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@matches_bp.route('/user/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user_matches(user_id):
    """
    Get all computed matches for user
    
    Query Parameters:
    - min_score: Filter by minimum score (default 50)
    - sort_by: Sort by 'score' (default) or 'date'
    - limit: Max results (default 20)
    - offset: Pagination offset (default 0)
    
    Returns:
    {
        "matches": [
            {
                "score_id": 1,
                "user_a_id": 123,
                "user_b_id": 456,
                "overall_score": 82,
                "compatibility_label": "Very Good Match",
                "components": {...}
            },
            ...
        ],
        "total": 15,
        "limit": 20,
        "offset": 0
    }
    """
    try:
        current_user = int(get_jwt_identity())
        
        # Users can only view their own matches
        if current_user != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        min_score = int(request.args.get('min_score', 50))
        sort_by = request.args.get('sort_by', 'score')
        
        # Get matches where user is either user_a or user_b
        query = CompatibilityScore.query.filter(
            db.or_(
                CompatibilityScore.user_a_id == user_id,
                CompatibilityScore.user_b_id == user_id
            )
        )
        query = query.filter(CompatibilityScore.overall_score >= min_score)
        
        if sort_by == 'score':
            query = query.order_by(CompatibilityScore.overall_score.desc())
        elif sort_by == 'date':
            query = query.order_by(CompatibilityScore.computed_at.desc())
        
        # Pagination
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = int(request.args.get('offset', 0))
        
        total = query.count()
        scores = query.limit(limit).offset(offset).all()
        
        matches = []
        for score in scores:
            # Determine the other user in this pair
            other_user_id = score.user_b_id if score.user_a_id == user_id else score.user_a_id
            match_user = User.query.get(other_user_id)
            matches.append({
                'score_id': score.score_id,
                'user_a_id': score.user_a_id,
                'user_b_id': score.user_b_id,
                'overall_score': score.overall_score,
                'compatibility_label': score.get_strength_description(),
                'strongest_component': score.get_strongest_component(),
                'components': score.get_component_breakdown(),
                'match_user': match_user.to_dict() if match_user else None,
                'computed_at': score.computed_at.isoformat() if score.computed_at else None
            })
        
        return jsonify({
            'matches': matches,
            'total': total,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@matches_bp.route('/<int:user_id_1>/<int:user_id_2>', methods=['POST'])
@jwt_required()
def score_users(user_id_1, user_id_2):
    """
    Score two specific users for compatibility
    
    Scoring Agent computes compatibility between two users
    
    Returns:
    {
        "score_id": 1,
        "user_a_id": 123,
        "user_b_id": 456,
        "overall_score": 82,
        "components": {
            "cosine_similarity": 0.85,
            "lifestyle": 80,
            ...
        }
    }
    """
    try:
        # Get both users' vectors
        user1_vector = PreferenceVector.query.filter_by(user_id=user_id_1).first()
        user2_vector = PreferenceVector.query.filter_by(user_id=user_id_2).first()
        
        if not user1_vector or not user2_vector:
            return jsonify({'error': 'One or both users do not have preference vectors'}), 400
        
        # Compute similarity
        similarity = user1_vector.get_similarity_with(user2_vector)
        
        # Get preferences for real scoring
        prefs1 = UserPreference.query.filter_by(user_id=user_id_1).first()
        prefs2 = UserPreference.query.filter_by(user_id=user_id_2).first()
        
        CLEAN_MAP = {'Very Clean': 10, 'Clean': 7, 'Average': 5, 'Relaxed': 2}
        SCHED_COMPAT = {
            ('9-5 Job', '9-5 Job'): 95, ('Night Shift', 'Night Shift'): 95,
            ('Student', 'Student'): 90, ('Flexible', 'Flexible'): 85,
            ('9-5 Job', 'Student'): 70, ('Student', '9-5 Job'): 70,
            ('Flexible', '9-5 Job'): 75, ('9-5 Job', 'Flexible'): 75,
            ('Flexible', 'Student'): 75, ('Student', 'Flexible'): 75,
            ('Flexible', 'Night Shift'): 65, ('Night Shift', 'Flexible'): 65,
            ('9-5 Job', 'Night Shift'): 30, ('Night Shift', '9-5 Job'): 30,
            ('Student', 'Night Shift'): 45, ('Night Shift', 'Student'): 45,
        }
        
        # Real sub-score computation
        lifestyle_score = 50
        schedule_score = 60
        budget_score = 50
        habits_score = 50
        age_match_score = 70
        
        if prefs1 and prefs2:
            # Lifestyle
            user1 = User.query.get(user_id_1)
            user2 = User.query.get(user_id_2)
            if user1 and user2 and user1.city and user2.city and user1.city.lower() == user2.city.lower():
                lifestyle_score += 20
            c1 = CLEAN_MAP.get(prefs1.cleanliness_level, 5)
            c2 = CLEAN_MAP.get(prefs2.cleanliness_level, 5)
            cgap = abs(c1 - c2)
            if cgap == 0: lifestyle_score += 20
            elif cgap <= 2: lifestyle_score += 15
            elif cgap <= 4: lifestyle_score += 8
            ngap = abs(int(prefs1.noise_tolerance or 5) - int(prefs2.noise_tolerance or 5))
            if ngap <= 2: lifestyle_score += 10
            elif ngap <= 4: lifestyle_score += 5
            lifestyle_score = min(100, lifestyle_score)
            
            # Schedule
            s1 = prefs1.schedule or 'Flexible'
            s2 = prefs2.schedule or 'Flexible'
            schedule_score = SCHED_COMPAT.get((s1, s2), 55)
            
            # Budget
            try:
                a_min, a_max = float(prefs1.budget_min or 300), float(prefs1.budget_max or 1500)
                b_min, b_max = float(prefs2.budget_min or 300), float(prefs2.budget_max or 1500)
                o_min, o_max = max(a_min, b_min), min(a_max, b_max)
                if o_min > o_max:
                    budget_score = 20
                else:
                    o_range = o_max - o_min
                    pct = min(o_range / max(a_max - a_min, 1), o_range / max(b_max - b_min, 1))
                    budget_score = min(100, int(40 + (pct * 60)))
            except:
                pass
            
            # Habits
            habits_score = 100
            if prefs1.smoking_ok != prefs2.smoking_ok: habits_score -= 35
            if prefs1.pets_ok != prefs2.pets_ok: habits_score -= 25
            if cgap >= 5: habits_score -= 20
            elif cgap >= 3: habits_score -= 10
            habits_score = max(0, habits_score)
            
            # Age match
            try:
                a_min_a, a_max_a = int(prefs1.age_min or 18), int(prefs1.age_max or 65)
                b_min_a, b_max_a = int(prefs2.age_min or 18), int(prefs2.age_max or 65)
                o_min_a, o_max_a = max(a_min_a, b_min_a), min(a_max_a, b_max_a)
                if o_min_a > o_max_a:
                    age_match_score = 20
                else:
                    o_range = o_max_a - o_min_a
                    pct = min(o_range / max(a_max_a - a_min_a, 1), o_range / max(b_max_a - b_min_a, 1))
                    age_match_score = min(100, int(40 + (pct * 60)))
            except:
                pass
        
        overall_score = int(
            similarity * 100 * 0.3 +
            lifestyle_score * 0.2 +
            schedule_score * 0.2 +
            budget_score * 0.15 +
            habits_score * 0.15
        )
        
        # Check or create score
        score = CompatibilityScore.query.filter(
            ((CompatibilityScore.user_a_id == user_id_1) & (CompatibilityScore.user_b_id == user_id_2)) |
            ((CompatibilityScore.user_a_id == user_id_2) & (CompatibilityScore.user_b_id == user_id_1))
        ).first()
        
        if score:
            score.overall_score = overall_score
            score.lifestyle_score = lifestyle_score
            score.schedule_score = schedule_score
            score.budget_score = budget_score
            score.habits_score = habits_score
            score.age_match_score = age_match_score
            score.computed_at = datetime.utcnow()
        else:
            score = CompatibilityScore(
                user_a_id=user_id_1,
                user_b_id=user_id_2,
                overall_score=overall_score,
                lifestyle_score=lifestyle_score,
                schedule_score=schedule_score,
                budget_score=budget_score,
                habits_score=habits_score,
                age_match_score=age_match_score,
                computed_at=datetime.utcnow()
            )
            db.session.add(score)
        
        db.session.commit()
        
        return jsonify({
            'score_id': score.score_id,
            'user_a_id': score.user_a_id,
            'user_b_id': score.user_b_id,
            'overall_score': score.overall_score,
            'components': score.get_component_breakdown()
        }), 200 if not isinstance(score.score_id, type(None)) else 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@matches_bp.route('/<int:score_id>', methods=['DELETE'])
@jwt_required()
def delete_score(score_id):
    """
    Delete cached compatibility score
    
    This will force a recomputation next time matching is triggered
    
    Returns:
    {
        "message": "Score deleted",
        "score_id": 5
    }
    """
    try:
        score = CompatibilityScore.query.get(score_id)
        if not score:
            return jsonify({'error': 'Score not found'}), 404
        
        # Verify ownership (user_a can delete)
        current_user = int(get_jwt_identity())
        if score.user_a_id != current_user:
            return jsonify({'error': 'Unauthorized'}), 403
        
        db.session.delete(score)
        db.session.commit()
        
        return jsonify({
            'message': 'Score deleted',
            'score_id': score_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@matches_bp.route('/conflicts/<int:user_id_1>/<int:user_id_2>', methods=['GET'])
@jwt_required()
def check_conflicts(user_id_1, user_id_2):
    """
    Check for conflicts between two users
    
    Conflict Detection Agent output
    
    Returns:
    {
        "has_hard_conflicts": false,
        "has_soft_conflicts": true,
        "conflicts": [
            {
                "conflict_id": 1,
                "type": "soft",
                "severity": 4,
                "reason": "Schedule mismatch",
                "details": "..."
            }
        ]
    }
    """
    try:
        conflicts = ConflictLog.get_conflicts_for_pair(user_id_1, user_id_2)
        
        has_hard = any(c.is_hard_conflict() for c in conflicts)
        has_soft = any(c.is_soft_conflict() for c in conflicts)
        
        return jsonify({
            'has_hard_conflicts': has_hard,
            'has_soft_conflicts': has_soft,
            'conflict_count': len(conflicts),
            'conflicts': [
                {
                    'conflict_id': c.conflict_id,
                    'type': c.conflict_type,
                    'severity': c.severity,
                    'severity_label': c.get_severity_label(),
                    'description': c.description,
                    'auto_generated_at': c.auto_generated_at.isoformat() if c.auto_generated_at else None
                }
                for c in conflicts
            ]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
