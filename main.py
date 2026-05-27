"""DevRelay 应用入口。"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import APIRouter

from app import __version__
from app.config import get_settings
from app.database import close_db, init_db
from app.routers import api_router
from app.services.cache import close_redis

# 定时任务标记
_scheduler_task = None


async def _run_daily_digest():
    """每天早上 8:00 执行日报生成。"""
    while True:
        now = __import__("datetime").datetime.now()
        # 计算距离下一次 8:00 的秒数
        target = now.replace(hour=8, minute=0, second=0, microsecond=0)
        if now >= target:
            target = target + __import__("datetime").timedelta(days=1)
        wait_seconds = (target - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        try:
            from app.services.daily_digest import generate_daily_digest
            results = await generate_daily_digest()
            print(f"[DailyDigest] 生成 {len(results)} 份日报")
            for r in results:
                rid = r.get("report_id", "FAIL")
                err = r.get("error", "")
                print(f"  - {r.get('repo', '?')}: {'OK #' + str(rid) if rid else 'FAIL: ' + err}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[DailyDigest] 日报生成失败: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    # 启动定时日报任务
    global _scheduler_task
    _scheduler_task = asyncio.create_task(_run_daily_digest())

    yield

    if _scheduler_task:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass

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

        # 手动触发日报的端点
    digest_router = APIRouter()

    @digest_router.post("/digest/run")
    async def trigger_digest():
        """为所有活跃订阅生成日报。"""
        from app.services.daily_digest import generate_daily_digest
        results = await generate_daily_digest()
        return {"count": len(results), "results": results}

    @digest_router.post("/digest/run/{sub_id}")
    async def trigger_digest_single(sub_id: int):
        """为单个订阅生成日报。"""
        from app.services.daily_digest import generate_daily_digest
        results = await generate_daily_digest(sub_id=sub_id)
        return {"count": len(results), "results": results}

    app.include_router(digest_router, prefix=settings.api_prefix)

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
