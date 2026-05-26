"""
健康检查 API 测试。

验证 GET /api/v1/health 端点是否正常工作。
"""

import pytest
from httpx import AsyncClient


class TestHealthCheck:
    """健康检查接口测试"""

    @pytest.mark.asyncio
    async def test_health_returns_ok(self, async_client: AsyncClient):
        """GET /api/v1/health 应返回 status=ok"""
        resp = await async_client.get("/api/v1/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert isinstance(data["app"], str) and len(data["app"]) > 0
        assert "version" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_health_returns_valid_version(self, async_client: AsyncClient):
        """健康检查应返回有效的版本号"""
        from app import __version__

        resp = await async_client.get("/api/v1/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == __version__

    @pytest.mark.asyncio
    async def test_health_response_model(self, async_client: AsyncClient):
        """验证响应字段类型正确"""
        resp = await async_client.get("/api/v1/health")

        data = resp.json()
        assert isinstance(data["status"], str)
        assert isinstance(data["app"], str)
        assert isinstance(data["version"], str)
        assert isinstance(data["timestamp"], str)

    @pytest.mark.asyncio
    async def test_health_wrong_method(self, async_client: AsyncClient):
        """POST /api/v1/health 应返回 405 Method Not Allowed"""
        resp = await async_client.post("/api/v1/health")

        assert resp.status_code == 405
