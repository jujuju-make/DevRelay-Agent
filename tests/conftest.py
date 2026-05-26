"""
pytest 全局配置和 fixtures（夹具）。

这里的 fixtures 是整个测试套件的"基础设施"，
会在每个测试函数运行前自动注入。
"""

import os
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# ═══════════════════════════════════════════════
# 测试环境变量（必须在导入 app 前设置）
# ═══════════════════════════════════════════════
# 让 Settings() 在测试时使用这些值，避免依赖真实的 .env 文件
os.environ["DATABASE_URL"] = "mysql+aiomysql://test:test@localhost:3306/test_db"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["OPENAI_API_KEY"] = "sk-test-fake-key"
os.environ["OPENAI_MODEL"] = "gpt-4"
os.environ["GITHUB_TOKEN"] = "ghp_test_token"
os.environ["SERPER_API_KEY"] = "test-serper-key"

# 必须在其他 app 导入之前设置，否则 config.py 中的 @lru_cache 会缓存空值
from app.config import get_settings
settings = get_settings()  # 触发缓存


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    """每个测试后清除 Settings 缓存，避免测试间相互影响。"""
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _mock_db_lifespan(monkeypatch):
    """阻止 app 启动时连接 MySQL（lifespan 中的 init_db）。"""
    monkeypatch.setattr("app.database.init_db", AsyncMock())
    monkeypatch.setattr("app.database.close_db", AsyncMock())
    # 阻止创建真正的 engine
    monkeypatch.setattr("app.database.create_async_engine", lambda url, **kwargs: None)


@pytest.fixture
def mock_redis(monkeypatch):
    """
    模拟 Redis 客户端，不依赖真实 Redis 服务。

    用法：在测试函数中通过 mock_redis 修改返回值：
        mock_redis["get"] = AsyncMock(return_value=json.dumps([...]))
    """
    redis_mock = {
        "get": AsyncMock(return_value=None),
        "setex": AsyncMock(),
        "lpush": AsyncMock(),
        "expire": AsyncMock(),
        "ping": AsyncMock(return_value=True),
        "aclose": AsyncMock(),
        "from_url": AsyncMock(),
    }

    # 模拟 get_redis() 返回 mock 对象
    mock_client = AsyncMock()
    for attr, val in redis_mock.items():
        setattr(mock_client, attr, val)

    monkeypatch.setattr("app.services.cache.get_redis", AsyncMock(return_value=mock_client))
    monkeypatch.setattr("app.services.chat_memory.get_chat_history", AsyncMock())

    return mock_client


@pytest.fixture
def mock_db_session(monkeypatch):
    """
    模拟数据库 session，不依赖真实 MySQL。
    同时阻止 SQLAlchemy engine 的创建。
    """
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.add = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh.return_value = None
    mock_session.execute = AsyncMock()

    # session factory 返回的 factory 本身是可调用的，返回 session
    mock_factory_call = AsyncMock()
    mock_factory_call.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory_call.__aexit__ = AsyncMock(return_value=None)
    mock_factory = lambda: mock_factory_call

    # 多个模块都 import 引用了 get_session_factory，所以都需要 mock
    monkeypatch.setattr("app.database.get_session_factory", lambda: mock_factory)
    monkeypatch.setattr("app.tools.github.get_session_factory", lambda: mock_factory)
    monkeypatch.setattr("app.routers.reports.get_session_factory", lambda: mock_factory)

    return mock_session


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    提供 FastAPI 测试客户端。

    用法：
        resp = await async_client.get("/api/v1/health")
        resp = await async_client.post("/api/v1/agent/run", json={...})
    """
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_httpx(monkeypatch):
    """
    模拟 httpx 请求，不依赖真实网络。
    默认 json() 返回 GitHub commits 格式的 list。
    """
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = lambda: [
        {
            "sha": "abc123def456789",
            "commit": {
                "message": "Fix bug in parser",
                "author": {"name": "Alice", "date": "2025-01-15T10:00:00Z"},
            },
        }
    ]
    mock_response.text = "mock content"
    mock_response.raise_for_status = lambda: None
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.post = AsyncMock(return_value=mock_response)

    monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: mock_client)

    return mock_response

