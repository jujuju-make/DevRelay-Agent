from fastapi import APIRouter

from app.routers import agent, health, reports, subscriptions

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])
