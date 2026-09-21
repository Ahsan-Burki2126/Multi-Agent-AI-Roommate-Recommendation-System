"""
Flask Application Factory
Initializes the Flask app, database, and error handlers

This is the main entry point for the Roommate Matching System.
The app creates and configures all components including:
- Database models
- API routes
- Error handlers
- CORS configuration
"""

import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
from backend.database import db

# Load environment variables from .env file (check project dir and parent dir)
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', '.env'))

# JWT Manager instance
jwt = JWTManager()


def create_app(config_name=None):
    """
    Application factory function.
    Creates and configures the Flask application.
    
    Args:
        config_name: 'development', 'testing', or 'production'
                    Defaults to FLASK_ENV environment variable
    
    Returns:
        Configured Flask application
    
    Example:
        app = create_app('development')
        app.run(debug=True)
    """
    
    # Import here to avoid circular imports
    from backend.config import get_config
    
    # Create Flask app
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(get_config(config_name))
    
    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    CORS(app, origins="*", supports_credentials=True, allow_headers=["Content-Type", "Authorization"], methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    
    # Register database models
    _register_models(app)
    
    # Register blueprints (routes)
    _register_routes(app)
    
    # Register error handlers
    _register_error_handlers(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app


def _register_models(app):
    """
    Import and register all database models with SQLAlchemy.
    This ensures the database knows about all tables.
    
    Models are in: backend/models/*.py
    """
    with app.app_context():
        # Import all models to register them with SQLAlchemy
        from backend.models.user import User
        from backend.models.preference import UserPreference, PreferenceVector
        from backend.models.room import Room
        from backend.models.score import CompatibilityScore
        from backend.models.match import Recommendation
        from backend.models.conflict import ConflictLog
        from backend.models.audit import AuditLog


def _register_routes(app):
    """
    Register all API route blueprints.
    Routes are organized by resource:
    - /auth/* - Authentication
    - /users/* - User management
    - /preferences/* - Preference management
    - /rooms/* - Room listing
    - /matches/* - Matching engine
    - /recommendations/* - Recommendations
    """
    
    # Try to import routes - these are created in Phase 3
    try:
        from backend.routes.auth import auth_bp
        app.register_blueprint(auth_bp, url_prefix='/auth')
    except ImportError:
        pass
    
    try:
        from backend.routes.users import users_bp
        app.register_blueprint(users_bp, url_prefix='/users')
    except ImportError:
        pass
    
    try:
        from backend.routes.preferences import preferences_bp
        app.register_blueprint(preferences_bp, url_prefix='/preferences')
    except ImportError:
        pass
    
    try:
        from backend.routes.rooms import rooms_bp
        app.register_blueprint(rooms_bp, url_prefix='/rooms')
    except ImportError:
        pass
    
    try:
        from backend.routes.matching import matches_bp
        app.register_blueprint(matches_bp, url_prefix='/matches')
    except ImportError:
        pass
    
    try:
        from backend.routes.recommendations import recommendations_bp
        app.register_blueprint(recommendations_bp, url_prefix='/recommendations')
    except ImportError:
        pass
    
    try:
        from backend.routes.orchestrate import orchestrate_bp
        app.register_blueprint(orchestrate_bp, url_prefix='/orchestrate')
    except ImportError:
        pass
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        """Simple health check endpoint for monitoring"""
        return jsonify({
            'status': 'healthy',
            'message': 'Roommate Matching System API is running'
        }), 200

    # Serve frontend static files
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')

    @app.route('/', defaults={'filename': 'index.html'})
    @app.route('/<path:filename>')
    def serve_frontend(filename):
        return send_from_directory(frontend_dir, filename)


def _register_error_handlers(app):
    """
    Register custom error handlers for common errors.
    Ensures consistent error response format.
    """
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 - Resource Not Found"""
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource does not exist'
        }), 404
    
    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 - Bad Request"""
        return jsonify({
            'error': 'Bad Request',
            'message': 'Invalid request parameters'
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        """Handle 401 - Unauthorized"""
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Authentication required'
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        """Handle 403 - Forbidden"""
        return jsonify({
            'error': 'Forbidden',
            'message': 'You do not have permission to access this resource'
        }), 403
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 - Internal Server Error"""
        db.session.rollback()
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        }), 500
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle unexpected errors"""
        app.logger.error(f'Unexpected error: {str(error)}')
        return jsonify({
            'error': 'Server Error',
            'message': 'An unexpected error occurred. Please try again later.'
        }), 500


if __name__ == '__main__':
    """
    Entry point when running app.py directly.
    
    Usage:
        python app.py              # Run on default (5000)
        FLASK_ENV=production python app.py
    """
    import sys
    
    # Get environment from command line or env variable
    config_name = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Create and run app
    app = create_app(config_name)
    
    # Run with debug mode based on config
    debug = app.config.get('DEBUG', False)
    print(f">> Starting Roommate Matching System (DEBUG={debug})")
    print(f"   Environment: {app.config.__class__.__name__}")
    print(f"   Database: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not configured')}")
    print(f"   Listening on: http://localhost:5000")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=debug
    )
