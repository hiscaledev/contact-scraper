"""API router aggregator."""
from fastapi import APIRouter
from app.api.routes import contact, csv

api_router = APIRouter()

# Include all route modules
api_router.include_router(contact.router)
api_router.include_router(csv.router, prefix="/csv")
