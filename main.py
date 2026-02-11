# Root-level entry point for Render deployment
# Render's start command uses: uvicorn main:app
# This file re-exports the FastAPI app from the app package
from app.main import app
