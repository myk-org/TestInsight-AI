"""Main API router aggregator for TestInsight AI."""

from fastapi import APIRouter

from backend.api.routers import ai, analysis, jenkins, settings, system

# Create main API router
router = APIRouter()

# Include all sub-routers
router.include_router(analysis.router)
router.include_router(jenkins.router)
router.include_router(ai.router)
router.include_router(settings.router)
router.include_router(system.router)
