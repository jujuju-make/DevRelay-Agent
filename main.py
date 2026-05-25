"""DevRelay 应用入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.config import get_settings
from app.database import close_db, init_db
from app.routers import api_router
from app.services.cache import close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_redis()
    await close_db()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="监控 GitHub 与技术博客更新的异步 Agent 服务",
        lifespan=lifespan,
        debug=settings.debug,
    )
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
