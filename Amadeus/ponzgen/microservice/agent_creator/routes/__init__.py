"""
Routes Package for Agent Field Autofill

This package provides the API routes for the agent field autofill microservice.
"""

from fastapi import APIRouter

from .autofill import router as autofill_router
from .user_input_routes import router as user_input_router

# Create main router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(autofill_router)
api_router.include_router(user_input_router)
