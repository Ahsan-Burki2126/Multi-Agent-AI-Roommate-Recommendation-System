import sys
import os

# Change to the backend directory
backend_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(backend_dir)

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(backend_dir))

from backend.app import create_app
from backend.database import db

app = create_app()
with app.app_context():
    db.create_all()
    print("Database initialized successfully!")
