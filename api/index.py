"""
Vercel Serverless Entry Point
==============================
Vercel's Python runtime looks for `app` in this file.
We import the Flask app factory and expose the WSGI app.

Environment variables to set in Vercel Dashboard:
  FLASK_ENV            = production
  SECRET_KEY           = <random 32-char string>
  JWT_SECRET_KEY       = <different random 32-char string>
  DATABASE_URL         = <postgres connection string from Neon/Supabase>
  GOOGLE_API_KEY       = <Google AI Studio API key>
  GEMINI_MODEL         = gemini-2.0-flash
  CORS_ORIGINS         = https://your-vercel-domain.vercel.app
"""
import sys
import os

# Ensure project root is on the Python path so `backend` package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import create_app

# Create the Flask application (Vercel imports `app` directly)
app = create_app('production')

# Vercel calls this as a WSGI handler
if __name__ == '__main__':
    app.run()
