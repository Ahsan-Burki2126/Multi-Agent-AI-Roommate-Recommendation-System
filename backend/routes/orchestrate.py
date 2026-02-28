"""
Orchestration Routes
Exposes agent pipeline execution as API endpoints.

These routes trigger the multi-agent system to execute matching and room search pipelines.

Endpoints:
- POST /orchestrate/matches - Find all matches for user
- POST /orchestrate/rooms - Find all rooms for user
- GET /orchestrate/status - Get agent system status
- GET /orchestrate/execution-log - Get execution history
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import json

orchestrate_bp = Blueprint('orchestrate', __name__)


def _get_orchestrator():
    """Lazy-load orchestrator inside request context to avoid import-time errors."""
    from backend.agents import get_orchestrator
    return get_orchestrator()


@orchestrate_bp.route('/matches', methods=['POST'])
@jwt_required()
def execute_matches_pipeline():
    """
    Execute full matching pipeline for current user.
    
    Triggers:
    1. User Profiling Agent - Validate user exists
    2. Preference Analysis Agent - Vectorize preferences
    3. Compatibility Scoring Agent - Score all candidates
    4. Conflict Detection Agent - Filter hard blockers
    5. Recommendation Engine Agent - Generate ranked recommendations
    
    Request JSON:
    {
        "min_score": 60,      # Minimum compatibility score (0-100)
        "limit": 20           # Max recommendations to return
    }
    
    Returns:
    {
        "success": true,
        "user_id": 123,
        "recommendations": [
            {
                "user_id": 456,
                "score": 82,
                "user_name": "Alice",
                "strength": "Very Good Match",
                "explanation": {...}
            }
        ],
        "metrics": {
            "scores_computed": 45,
            "recommendations_generated": 12
        }
    }
    """
    try:
        current_user = int(get_jwt_identity())
        data = request.get_json() or {}
        
        min_score = int(data.get('min_score', 60))
        limit = int(data.get('limit', 20))
        
        # Validate parameters
        if not 0 <= min_score <= 100:
            return jsonify({'error': 'min_score must be between 0 and 100'}), 400
        
        if limit < 1 or limit > 100:
            return jsonify({'error': 'limit must be between 1 and 100'}), 400
        
        # Execute pipeline
        results = _get_orchestrator().find_matches_for_user(
            user_id=current_user,
            min_score=min_score
        )
        
        return jsonify({
            'success': results['success'],
            'user_id': current_user,
            'recommendations': results['recommendations'][:limit],
            'count': min(len(results['recommendations']), limit),
            'metrics': results['metrics'],
            'executed_at': datetime.utcnow().isoformat()
        }), 200 if (results['success'] or results['recommendations']) else 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@orchestrate_bp.route('/rooms', methods=['POST'])
@jwt_required()
def execute_rooms_pipeline():
    """
    Execute room search pipeline for current user.
    
    Triggers:
    1. User Profiling Agent - Validate user exists
    2. Room Matching Agent - Filter suitable rooms
    3. Conflict Detection Agent - Check user-room compatibility
    
    Request JSON:
    {
        "limit": 20  # Max rooms to return
    }
    
    Returns:
    {
        "success": true,
        "user_id": 123,
        "rooms": [
            {
                "room_id": 1,
                "title": "Cozy bedroom near downtown",
                "rent_price": 550,
                "location": "Toronto",
                "match_score": 85,
                "conflicts": []
            }
        ]
    }
    """
    try:
        current_user = int(get_jwt_identity())
        data = request.get_json() or {}
        
        limit = int(data.get('limit', 20))
        
        if limit < 1 or limit > 100:
            return jsonify({'error': 'limit must be between 1 and 100'}), 400
        
        # Execute pipeline
        results = _get_orchestrator().find_rooms_for_user(
            user_id=current_user,
            limit=limit
        )
        
        return jsonify({
            'success': results['success'],
            'user_id': current_user,
            'rooms': results['rooms'],
            'count': len(results['rooms']),
            'executed_at': datetime.utcnow().isoformat()
        }), 200 if results['success'] else 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@orchestrate_bp.route('/status', methods=['GET'])
def get_system_status():
    """
    Get status of all agents in the system.
    
    Returns:
    {
        "agents": {
            "User Profiling Agent": {
                "name": "User Profiling Agent",
                "version": "1.0",
                "status": "idle"
            },
            ...
        },
        "execution_summary": {
            "total_executions": 150,
            "success_rate": 95.3,
            "by_agent": {...}
        }
    }
    """
    try:
        orchestrator = _get_orchestrator()
        agent_statuses = orchestrator.get_agent_status()
        execution_summary = orchestrator.get_execution_summary()
        
        return jsonify({
            'agents': agent_statuses,
            'execution_summary': execution_summary,
            'system_status': 'operational',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@orchestrate_bp.route('/execution-log', methods=['GET'])
@jwt_required()
def get_execution_log():
    """
    Get execution log of recent agent runs.
    
    Query Parameters:
    - limit: Max log entries to return (default 50)
    
    Returns:
    {
        "log": [
            {
                "agent": "Compatibility Scoring Agent",
                "timestamp": "2024-01-15T10:30:00",
                "status": "success",
                "has_error": false
            }
        ],
        "summary": {
            "total": 150,
            "successful": 142,
            "failed": 8
        }
    }
    """
    try:
        limit = int(request.args.get('limit', 50))
        limit = min(limit, 1000)  # Max 1000
        
        orchestrator = _get_orchestrator()
        execution_log = orchestrator.get_execution_log(last_n=limit)
        summary = orchestrator.get_execution_summary()
        
        return jsonify({
            'log': execution_log,
            'limit': limit,
            'returned': len(execution_log),
            'summary': summary,
            'retrieved_at': datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@orchestrate_bp.route('/clear-log', methods=['POST'])
@jwt_required()
def clear_execution_log():
    """
    Clear the orchestrator execution log.
    
    Requires JWT authentication (admin-like operation).
    
    Returns:
    {
        "message": "Execution log cleared",
        "cleared_at": "..."
    }
    """
    try:
        current_user = int(get_jwt_identity())
        
        # In production, check if user is admin
        # For now, allow any authenticated user to view log
        
        _get_orchestrator().clear_execution_log()
        
        return jsonify({
            'message': 'Execution log cleared',
            'cleared_by': current_user,
            'cleared_at': datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@orchestrate_bp.route('/agent/<agent_name>/status', methods=['GET'])
def get_agent_status(agent_name):
    """
    Get status of a specific agent.
    
    Args:
        agent_name: Name of agent (URL parameter)
    
    Returns:
    {
        "name": "Compatibility Scoring Agent",
        "version": "1.0",
        "status": "idle",
        "last_result": {...}
    }
    """
    try:
        agent = _get_orchestrator().get_agent(agent_name)
        
        if not agent:
            return jsonify({'error': f'Agent not found: {agent_name}'}), 404
        
        return jsonify(agent.get_status()), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@orchestrate_bp.route('/pipeline-info', methods=['GET'])
def get_pipeline_info():
    """
    Get information about available agent pipelines.
    
    Returns:
    {
        "pipelines": [
            {
                "name": "Find Matches",
                "endpoint": "POST /orchestrate/matches",
                "agents": ["Profiling", "Analysis", "Scoring", "Conflict", "Recommendation"],
                "parameters": {...}
            }
        ]
    }
    """
    try:
        pipelines = [
            {
                'name': 'Find Matches Pipeline',
                'endpoint': 'POST /orchestrate/matches',
                'description': 'Find compatible roommates for a user',
                'agents': [
                    'User Profiling Agent',
                    'Preference Analysis Agent',
                    'Compatibility Scoring Agent',
                    'Conflict Detection Agent',
                    'Recommendation Engine Agent'
                ],
                'parameters': {
                    'min_score': {
                        'type': 'integer',
                        'default': 60,
                        'description': 'Minimum compatibility score (0-100)'
                    },
                    'limit': {
                        'type': 'integer',
                        'default': 20,
                        'description': 'Max recommendations to return'
                    }
                }
            },
            {
                'name': 'Find Rooms Pipeline',
                'endpoint': 'POST /orchestrate/rooms',
                'description': 'Find suitable rooms for a user',
                'agents': [
                    'User Profiling Agent',
                    'Room Matching Agent',
                    'Conflict Detection Agent'
                ],
                'parameters': {
                    'limit': {
                        'type': 'integer',
                        'default': 20,
                        'description': 'Max rooms to return'
                    }
                }
            }
        ]
        
        return jsonify({
            'pipelines': pipelines,
            'available_agents': list(_get_orchestrator().agents.keys()),
            'total_agents': len(_get_orchestrator().agents)
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
