"""
Configuration management for the Roommate Matching System
Handles different environments (development, testing, production)
"""
import os
import ssl
from datetime import timedelta

class Config:
    """Base configuration - shared by all environments"""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=30)
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Security
    BCRYPT_LOG_ROUNDS = 10
    
    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5000,http://localhost:3000').split(',')
    
    # File Upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads/')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Agent Configuration
    CACHE_VECTORS = True  # Cache preference vectors
    CACHE_SCORES = True   # Cache compatibility scores
    CACHE_EXPIRY = 2592000  # 30 days in seconds
    
    # Google Gemini (LangChain LLM)
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
    
    # Scoring Weights
    SCORING_WEIGHTS = {
        'preference_similarity': 0.3,
        'lifestyle_match': 0.2,
        'schedule_compatibility': 0.2,
        'budget_alignment': 0.15,
        'habits_alignment': 0.15
    }

# Get the base directory for the database
BASEDIR = os.path.abspath(os.path.dirname(__file__))

class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEBUG = True
    TESTING = False
    
    # SQLite for development - use absolute path
    _db_path = os.path.join(BASEDIR, "database", "roommate_system.db")
    os.makedirs(os.path.dirname(_db_path), exist_ok=True)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        f'sqlite:///{_db_path}'
    )
    
    SESSION_COOKIE_SECURE = False  # Allow HTTP in dev
    
    # Verbose logging
    SQLALCHEMY_ECHO = True
    LOG_LEVEL = 'DEBUG'


class TestingConfig(Config):
    """Testing environment configuration"""
    DEBUG = False
    TESTING = True
    
    # In-memory SQLite for tests
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False
    
    # Use simple password hashing for faster tests
    BCRYPT_LOG_ROUNDS = 4


class ProductionConfig(Config):
    """Production environment configuration (Vercel / Render / Railway)"""
    DEBUG = False
    TESTING = False

    # DATABASE_URL must be set in Vercel environment variables.
    # Neon / Supabase / Railway give you a postgres:// URL.
    # Vercel Postgres uses postgres:// but SQLAlchemy needs postgresql://
    _raw_db_url = os.getenv('DATABASE_URL', '')
    # Normalise postgres:// → postgresql:// (Neon/Heroku shorthand)
    if _raw_db_url.startswith('postgres://'):
        _raw_db_url = _raw_db_url.replace('postgres://', 'postgresql://', 1)
    # Switch driver to pg8000 (pure-Python, works on Vercel Lambda)
    if _raw_db_url.startswith('postgresql://') and '+' not in _raw_db_url.split('://')[0]:
        _raw_db_url = _raw_db_url.replace('postgresql://', 'postgresql+pg8000://', 1)
    # Strip ?sslmode=... — pg8000 does NOT accept sslmode as a URL param;
    # SSL is passed via connect_args instead (see SQLALCHEMY_ENGINE_OPTIONS below).
    if '?' in _raw_db_url:
        from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
        _parsed = urlparse(_raw_db_url)
        _qs = {k: v for k, v in parse_qs(_parsed.query).items() if k != 'sslmode'}
        _raw_db_url = urlunparse(_parsed._replace(query=urlencode(_qs, doseq=True)))
    # Fallback: /tmp is the only writable path on Vercel's read-only filesystem
    SQLALCHEMY_DATABASE_URI = _raw_db_url or 'sqlite:////tmp/production.db'

    # Neon requires SSL; pg8000 uses ssl_context (not sslmode URL param).
    # NullPool is mandatory for serverless — each Lambda invocation is independent.
    _ssl_ctx = ssl.create_default_context()
    from sqlalchemy.pool import NullPool
    SQLALCHEMY_ENGINE_OPTIONS = {
        'poolclass': NullPool,
        'connect_args': {'ssl_context': _ssl_ctx},
    }

    # Disable SQL echo in production for performance
    SQLALCHEMY_ECHO = False

    # Enforce HTTPS cookies
    SESSION_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = 'https'

    LOG_LEVEL = 'WARNING'


# Config selection based on environment
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config(config_name=None):
    """
    Get configuration object based on environment
    
    Args:
        config_name: 'development', 'testing', or 'production'
        If None, uses FLASK_ENV environment variable
    
    Returns:
        Configuration object
    """
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    return config.get(config_name, config['default'])
