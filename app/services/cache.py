"""Redis 缓存服务。"""

import json
from typing import Any

import redis.asyncio as aioredis

from app.config import get_settings

COMMITS_CACHE_TTL_SECONDS = 600  # 10 分钟

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


def commits_cache_key(
    owner: str,
    repo: str,
    per_page: int,
    sha: str | None = None,
) -> str:
    sha_part = sha or ""
    return f"devrelay:commits:{owner}:{repo}:{per_page}:{sha_part}"


async def get_cached_commits(cache_key: str) -> list[dict[str, Any]] | None:
    """从 Redis 读取 commit 列表缓存，未命中或异常时返回 None。"""
    try:
        client = await get_redis()
        raw = await client.get(cache_key)
        if raw is None:
            return None
        data = json.loads(raw)
        if isinstance(data, list):
            return data
    except Exception:
        return None
    return None


async def set_cached_commits(
    cache_key: str,
    commits: list[dict[str, Any]],
    *,
    ttl: int = COMMITS_CACHE_TTL_SECONDS,
) -> None:
    """将 commit 列表写入 Redis，默认 10 分钟过期。"""
    try:
        client = await get_redis()
        await client.setex(cache_key, ttl, json.dumps(commits, ensure_ascii=False))
    except Exception:
        pass
