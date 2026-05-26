"""
Redis 缓存服务测试（cache.py）。

测试缓存键生成和缓存读写逻辑。
"""

import json
from unittest.mock import AsyncMock

import pytest


class TestCommitsCacheKey:
    """缓存键生成函数"""

    def test_cache_key_format(self):
        """缓存键格式正确"""
        from app.services.cache import commits_cache_key

        key = commits_cache_key("owner", "repo", 10)
        assert key == "devrelay:commits:owner:repo:10:"

    def test_cache_key_with_sha(self):
        """带 SHA 参数的缓存键"""
        from app.services.cache import commits_cache_key

        key = commits_cache_key("owner", "repo", 5, "main")
        assert key == "devrelay:commits:owner:repo:5:main"


class TestGetCachedCommits:
    """读取缓存测试"""

    @pytest.mark.asyncio
    async def test_cache_hit_returns_data(self, mock_redis):
        """缓存命中时返回解析后的数据"""
        from app.services.cache import get_cached_commits

        cached_data = [{"sha": "abc123"}]
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_data))

        result = await get_cached_commits("test:key")
        assert result == cached_data

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self, mock_redis):
        """缓存未命中时返回 None"""
        from app.services.cache import get_cached_commits

        mock_redis.get = AsyncMock(return_value=None)

        result = await get_cached_commits("test:key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_invalid_json_returns_none(self, mock_redis):
        """缓存数据不是有效 JSON 时返回 None"""
        from app.services.cache import get_cached_commits

        mock_redis.get = AsyncMock(return_value="not-json")

        result = await get_cached_commits("test:key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_not_a_list_returns_none(self, mock_redis):
        """缓存数据不是 list 时返回 None"""
        from app.services.cache import get_cached_commits

        mock_redis.get = AsyncMock(return_value=json.dumps({"not": "list"}))

        result = await get_cached_commits("test:key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_redis_error_returns_none(self, mock_redis):
        """Redis 异常时返回 None（不崩溃）"""
        from app.services.cache import get_cached_commits

        mock_redis.get = AsyncMock(side_effect=Exception("Redis down"))

        result = await get_cached_commits("test:key")
        assert result is None


class TestSetCachedCommits:
    """写入缓存测试"""

    @pytest.mark.asyncio
    async def test_set_cache_success(self, mock_redis):
        """写入缓存调用 setex"""
        from app.services.cache import set_cached_commits

        commits = [{"sha": "abc123"}]
        await set_cached_commits("test:key", commits)

        mock_redis.setex.assert_called_once()
        # 验证参数：(key, ttl, json_string)
        args, _ = mock_redis.setex.call_args
        assert args[0] == "test:key"
        assert args[1] == 600  # 默认 10 分钟
        assert json.loads(args[2]) == commits

    @pytest.mark.asyncio
    async def test_set_cache_custom_ttl(self, mock_redis):
        """可自定义 TTL"""
        from app.services.cache import set_cached_commits

        await set_cached_commits("test:key", [], ttl=300)

        args, _ = mock_redis.setex.call_args
        assert args[1] == 300

    @pytest.mark.asyncio
    async def test_set_cache_redis_error(self, mock_redis):
        """Redis 写入失败时不抛出异常"""
        from app.services.cache import set_cached_commits

        mock_redis.setex = AsyncMock(side_effect=Exception("Redis down"))

        # 不应抛出异常
        await set_cached_commits("test:key", [])
