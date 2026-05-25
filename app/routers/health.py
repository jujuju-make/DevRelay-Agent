from datetime import datetime

from fastapi import APIRouter

from app import __version__
from app.config import get_settings
from app.schemas.agent import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=__version__,
        timestamp=datetime.utcnow(),
    )
