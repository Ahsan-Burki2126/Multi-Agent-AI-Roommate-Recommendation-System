"""
Vercel Serverless Entry Point (Services preset)
================================================
With experimentalServices, Vercel looks for api/index.py inside the
entrypoint directory ('backend').  We add the project root to sys.path
so that all 'backend.*' imports in app.py resolve correctly.

Environment variables to set in Vercel Dashboard:
  FLASK_ENV       = production
  SECRET_KEY      = <random 32-char string>
  JWT_SECRET_KEY  = <different random 32-char string>
  DATABASE_URL    = <postgres connection string from Neon>
  GOOGLE_API_KEY  = <Google AI Studio API key>
  GEMINI_MODEL    = gemini-2.0-flash
"""
import sys
import os

# backend/api/index.py  →  backend/api/  →  backend/  →  project_root
_backend_api_dir = os.path.dirname(os.path.abspath(__file__))   # backend/api/
_backend_dir     = os.path.dirname(_backend_api_dir)             # backend/
_project_root    = os.path.dirname(_backend_dir)                 # project root

if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from backend.app import create_app

# Vercel imports `app` directly as the WSGI handler
app = create_app('production')

if __name__ == '__main__':
    app.run()
