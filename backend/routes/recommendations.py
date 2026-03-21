"""
Recommendations Routes
Handles recommendation display and user interactions.

Endpoints:
- GET /recommendations/user/<user_id> - Get recommendations (Recommendation Engine)
- GET /recommendations/user/<user_id>/new - Get unviewed recommendations
- GET /recommendations/<rec_id> - Get individual recommendation
- PUT /recommendations/<rec_id>/viewed - Mark as viewed
- PUT /recommendations/<rec_id>/liked - Mark as liked
- PUT /recommendations/<rec_id>/disliked - Mark as disliked
- DELETE /recommendations/<rec_id> - Remove recommendation
- GET /recommendations/user/<user_id>/stats - Recommendation statistics
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from backend.database import db
from backend.models import Recommendation, User, CompatibilityScore, AuditLog
import json

recommendations_bp = Blueprint('recommendations', __name__)


@recommendations_bp.route('/user/<int:user_id>', methods=['GET'])
@jwt_required()
def get_recommendations(user_id):
    """
    Get all recommendations for user
    
    Recommendation Engine output
    
    Query Parameters:
    - status: 'pending', 'viewed', 'liked', 'disliked', or empty for all
    - min_score: Filter by minimum compatibility score (default 50)
    - sort_by: 'score' (default), 'date', or 'updated'
    - limit: Max results (default 20)
    - offset: Pagination offset (default 0)
    
    Example URL: /recommendations/user/123?status=pending&min_score=70&limit=10
    
    Returns:
    {
        "recommendations": [
            {
                "rec_id": 1,
                "requester_id": 123,
                "recommended_user_id": 456,
                "score": 82,
                "status": "pending",
                "recommended_user": {
                    "user_id": 456,
                    "full_name": "Alice",
                    "city": "Toronto",
                    ...
                },
                "viewed_at": null,
                "liked_at": null,
                "created_at": "2024-01-15T10:30:00"
            }
        ],
        "total": 15,
        "pending_count": 5,
        "limit": 20,
        "offset": 0
    }
    """
    try:
        current_user = int(get_jwt_identity())
        
        # Users can only view their own recommendations
        if current_user != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Get filter parameters
        min_score = int(request.args.get('min_score', 50))
        sort_by = request.args.get('sort_by', 'score')
        
        # Build query
        query = Recommendation.query.filter_by(requester_id=user_id)
        
        # Filter by minimum score (use match_score directly)
        query = query.filter(Recommendation.match_score >= min_score)
        
        # Sorting
        if sort_by == 'date':
            query = query.order_by(Recommendation.created_at.desc())
        elif sort_by == 'updated':
            query = query.order_by(Recommendation.created_at.desc())
        else:  # score
            query = query.order_by(Recommendation.match_score.desc())
        
        # Pagination
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = int(request.args.get('offset', 0))
        
        total = query.count()
        pending_count = Recommendation.query.filter(
            Recommendation.requester_id == user_id,
            Recommendation.viewed_at == None
        ).count()
        
        recs = query.limit(limit).offset(offset).all()
        
        result_recs = []
        for rec in recs:
            # Get matched user info
            matched_user_data = None
            if rec.match_type == 'roommate':
                matched_user = User.query.get(rec.match_id)
                if not matched_user:
                    # Skip recommendations pointing to deleted users
                    continue
                matched_user_data = matched_user.to_dict()

            result_recs.append({
                'recommendation_id': rec.recommendation_id,
                'requester_id': rec.requester_id,
                'match_type': rec.match_type,
                'match_id': rec.match_id,
                'match_score': float(rec.match_score) if rec.match_score else 0,
                'explanation': rec.explanation,
                'matched_user': matched_user_data,
                'viewed_at': rec.viewed_at.isoformat() if rec.viewed_at else None,
                'liked': rec.liked,
                'created_at': rec.created_at.isoformat() if rec.created_at else None
            })
        
        return jsonify({
            'recommendations': result_recs,
            'total': total,
            'pending_count': pending_count,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@recommendations_bp.route('/user/<int:user_id>/new', methods=['GET'])
@jwt_required()
def get_new_recommendations(user_id):
    """
    Get unviewed recommendations for user
    
    Convenience endpoint for fetching new recommendations
    
    Query Parameters:
    - min_score: Filter by minimum score (default 60)
    - limit: Max results (default 10)
    
    Returns:
    {
        "new_count": 5,
        "recommendations": [...]  # Same format as get_recommendations
    }
    """
    try:
        current_user = int(get_jwt_identity())
        
        if current_user != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        min_score = int(request.args.get('min_score', 60))
        limit = min(int(request.args.get('limit', 10)), 100)
        
        # Get unviewed recommendations
        recs = Recommendation.query.filter(
            Recommendation.requester_id == user_id,
            Recommendation.viewed_at == None,
            Recommendation.match_score >= min_score
        ).order_by(
            Recommendation.match_score.desc()
        ).limit(limit).all()
        
        result_recs = []
        for rec in recs:
            matched_user_data = None
            if rec.match_type == 'roommate':
                matched_user = User.query.get(rec.match_id)
                if matched_user:
                    matched_user_data = matched_user.to_dict()
            
            result_recs.append({
                'recommendation_id': rec.recommendation_id,
                'match_id': rec.match_id,
                'match_score': float(rec.match_score) if rec.match_score else 0,
                'matched_user': matched_user_data,
                'created_at': rec.created_at.isoformat() if rec.created_at else None
            })
        
        return jsonify({
            'new_count': len(result_recs),
            'recommendations': result_recs
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@recommendations_bp.route('/<int:rec_id>', methods=['GET'])
@jwt_required()
def get_recommendation(rec_id):
    """
    Get individual recommendation details
    """
    try:
        current_user = int(get_jwt_identity())
        rec = Recommendation.query.get(rec_id)
        
        if not rec:
            return jsonify({'error': 'Recommendation not found'}), 404
        
        if rec.requester_id != current_user:
            return jsonify({'error': 'Unauthorized'}), 403
        
        matched_user_data = None
        if rec.match_type == 'roommate':
            matched_user = User.query.get(rec.match_id)
            if matched_user:
                matched_user_data = matched_user.to_dict()
        
        return jsonify({
            'recommendation_id': rec.recommendation_id,
            'requester_id': rec.requester_id,
            'match_type': rec.match_type,
            'match_id': rec.match_id,
            'match_score': float(rec.match_score) if rec.match_score else 0,
            'explanation': rec.explanation,
            'matched_user': matched_user_data,
            'viewed_at': rec.viewed_at.isoformat() if rec.viewed_at else None,
            'liked': rec.liked,
            'created_at': rec.created_at.isoformat() if rec.created_at else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@recommendations_bp.route('/<int:rec_id>/viewed', methods=['PUT'])
@jwt_required()
def mark_viewed(rec_id):
    """
    Mark recommendation as viewed
    """
    try:
        current_user = int(get_jwt_identity())
        rec = Recommendation.query.get(rec_id)
        
        if not rec:
            return jsonify({'error': 'Recommendation not found'}), 404
        
        if rec.requester_id != current_user:
            return jsonify({'error': 'Unauthorized'}), 403
        
        rec.viewed_at = datetime.utcnow()
        db.session.commit()
        
        # Log interaction
        audit = AuditLog(
            agent_name='Recommendation Engine',
            action='recommendation_viewed',
            entity_type='recommendation',
            entity_id=rec_id,
            details=json.dumps({'user_id': current_user}),
            timestamp=datetime.utcnow()
        )
        db.session.add(audit)
        db.session.commit()
        
        return jsonify({
            'recommendation_id': rec.recommendation_id,
            'viewed_at': rec.viewed_at.isoformat()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@recommendations_bp.route('/<int:recommendation_id>/liked', methods=['PUT'])
@jwt_required()
def mark_liked(recommendation_id):
    """
    Mark recommendation as liked
    
    This indicates user interest in the match
    
    Returns:
    {
        "recommendation_id": 1,
        "liked": true,
        "viewed_at": "2024-01-15T10:36:00"
    }
    """
    try:
        current_user = int(get_jwt_identity())
        rec = Recommendation.query.get(recommendation_id)
        
        if not rec:
            return jsonify({'error': 'Recommendation not found'}), 404
        
        if rec.requester_id != current_user:
            return jsonify({'error': 'Unauthorized'}), 403
        
        rec.liked = True
        rec.viewed_at = datetime.utcnow()
        
        db.session.commit()
        
        # Log interaction
        audit = AuditLog(
            agent_name='Recommendation Engine',
            action='recommendation_liked',
            entity_type='recommendation',
            entity_id=recommendation_id,
            details=json.dumps({'user_id': current_user}),
            timestamp=datetime.utcnow()
        )
        db.session.add(audit)
        db.session.commit()
        
        return jsonify({
            'recommendation_id': rec.recommendation_id,
            'liked': rec.liked,
            'viewed_at': rec.viewed_at.isoformat() if rec.viewed_at else None
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@recommendations_bp.route('/<int:recommendation_id>/disliked', methods=['PUT'])
@jwt_required()
def mark_disliked(recommendation_id):
    """
    Mark recommendation as disliked
    
    This indicates user is not interested in the match
    
    Returns:
    {
        "recommendation_id": 1,
        "liked": false,
        "viewed_at": "2024-01-15T10:37:00"
    }
    """
    try:
        current_user = int(get_jwt_identity())
        rec = Recommendation.query.get(recommendation_id)
        
        if not rec:
            return jsonify({'error': 'Recommendation not found'}), 404
        
        if rec.requester_id != current_user:
            return jsonify({'error': 'Unauthorized'}), 403
        
        rec.liked = False
        rec.viewed_at = datetime.utcnow()
        
        db.session.commit()
        
        # Log interaction
        audit = AuditLog(
            agent_name='Recommendation Engine',
            action='recommendation_disliked',
            entity_type='recommendation',
            entity_id=recommendation_id,
            details=json.dumps({'user_id': current_user}),
            timestamp=datetime.utcnow()
        )
        db.session.add(audit)
        db.session.commit()
        
        return jsonify({
            'recommendation_id': rec.recommendation_id,
            'liked': rec.liked,
            'viewed_at': rec.viewed_at.isoformat() if rec.viewed_at else None
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@recommendations_bp.route('/<int:recommendation_id>', methods=['DELETE'])
@jwt_required()
def delete_recommendation(recommendation_id):
    """
    Delete/dismiss recommendation
    
    This removes the recommendation from user's list
    
    Returns:
    {
        "message": "Recommendation deleted",
        "recommendation_id": 1
    }
    """
    try:
        current_user = int(get_jwt_identity())
        rec = Recommendation.query.get(recommendation_id)
        
        if not rec:
            return jsonify({'error': 'Recommendation not found'}), 404
        
        if rec.requester_id != current_user:
            return jsonify({'error': 'Unauthorized'}), 403
        
        rec_id_val = rec.recommendation_id
        db.session.delete(rec)
        db.session.commit()
        
        return jsonify({
            'message': 'Recommendation deleted',
            'recommendation_id': rec_id_val
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@recommendations_bp.route('/user/<int:user_id>/stats', methods=['GET'])
@jwt_required()
def get_recommendation_stats(user_id):
    """
    Get recommendation statistics for user
    
    Shows engagement metrics
    
    Returns:
    {
        "user_id": 123,
        "total_recommendations": 20,
        "pending": 8,
        "viewed": 10,
        "liked": 5,
        "disliked": 2,
        "deleted": 3,
        "engagement_rate": 0.65,
        "like_rate": 0.25,
        "avg_score_of_liked": 78,
        "avg_score_of_disliked": 52
    }
    """
    try:
        current_user = int(get_jwt_identity())
        
        if current_user != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        total = Recommendation.query.filter_by(requester_id=user_id).count()
        # pending = not viewed (viewed_at is None)
        pending = Recommendation.query.filter_by(requester_id=user_id).filter(Recommendation.viewed_at == None).count()
        # viewed = has viewed_at but no decision
        viewed = Recommendation.query.filter_by(requester_id=user_id, liked=None).filter(Recommendation.viewed_at != None).count()
        # liked = True
        liked_count = Recommendation.query.filter_by(requester_id=user_id, liked=True).count()
        # disliked = False
        disliked_count = Recommendation.query.filter_by(requester_id=user_id, liked=False).count()
        
        # Calculate engagement and like rates
        engaged = viewed + liked_count + disliked_count
        engagement_rate = engaged / total if total > 0 else 0
        like_rate = liked_count / engaged if engaged > 0 else 0
        
        # Average scores for liked recommendations
        liked_recs = Recommendation.query.filter_by(requester_id=user_id, liked=True).all()
        if liked_recs:
            liked_scores = []
            for rec in liked_recs:
                score = CompatibilityScore.query.filter(
                    ((CompatibilityScore.user_a_id == user_id) & 
                     (CompatibilityScore.user_b_id == rec.match_id)) |
                    ((CompatibilityScore.user_a_id == rec.match_id) & 
                     (CompatibilityScore.user_b_id == user_id))
                ).first()
                if score:
                    liked_scores.append(score.overall_score)
            avg_liked = sum(liked_scores) / len(liked_scores) if liked_scores else 0
        else:
            avg_liked = 0
        
        # Average scores for disliked recommendations
        disliked_recs = Recommendation.query.filter_by(requester_id=user_id, liked=False).all()
        if disliked_recs:
            disliked_scores = []
            for rec in disliked_recs:
                score = CompatibilityScore.query.filter(
                    ((CompatibilityScore.user_a_id == user_id) & 
                     (CompatibilityScore.user_b_id == rec.match_id)) |
                    ((CompatibilityScore.user_a_id == rec.match_id) & 
                     (CompatibilityScore.user_b_id == user_id))
                ).first()
                if score:
                    disliked_scores.append(score.overall_score)
            avg_disliked = sum(disliked_scores) / len(disliked_scores) if disliked_scores else 0
        else:
            avg_disliked = 0
        
        return jsonify({
            'user_id': user_id,
            'total_recommendations': total,
            'pending': pending,
            'viewed': viewed,
            'liked': liked_count,
            'disliked': disliked_count,
            'engagement_rate': round(engagement_rate, 2),
            'like_rate': round(like_rate, 2),
            'avg_score_of_liked': round(avg_liked, 1),
            'avg_score_of_disliked': round(avg_disliked, 1)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@recommendations_bp.route('/user/<int:user_id>/mutual', methods=['GET'])
@jwt_required()
def get_mutual_matches(user_id):
    """
    Get mutual matches — pairs where both users have liked each other's recommendation.

    Two users are a "mutual match" when:
    - User A has a recommendation for User B with liked=True
    - User B has a recommendation for User A with liked=True

    Returns:
    {
        "mutual_matches": [
            {
                "recommendation_id": 1,
                "match_id": 456,
                "match_score": 82.5,
                "matched_user": {...},
                "matched_at": "2024-01-15T10:30:00"
            }
        ],
        "count": 1
    }
    """
    try:
        current_user = int(get_jwt_identity())
        if current_user != user_id:
            return jsonify({'error': 'Unauthorized'}), 403

        # Find all recommendations where this user liked someone
        liked_by_me = Recommendation.query.filter_by(
            requester_id=user_id,
            liked=True,
            match_type='roommate'
        ).all()

        mutual = []
        for rec in liked_by_me:
            # Check if the other person also liked this user back
            reverse = Recommendation.query.filter_by(
                requester_id=rec.match_id,
                match_id=user_id,
                match_type='roommate',
                liked=True
            ).first()

            if reverse:
                matched_user = User.query.get(rec.match_id)
                if not matched_user:
                    continue
                mutual.append({
                    'recommendation_id': rec.recommendation_id,
                    'match_id': rec.match_id,
                    'match_score': float(rec.match_score) if rec.match_score else 0,
                    'matched_user': matched_user.to_dict(),
                    'matched_at': rec.viewed_at.isoformat() if rec.viewed_at else rec.created_at.isoformat()
                })

        return jsonify({
            'mutual_matches': mutual,
            'count': len(mutual)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
