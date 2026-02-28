"""
Database instance module
Separates db from app to avoid circular imports
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
