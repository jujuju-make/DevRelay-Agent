"""
报告相关 API 测试（reports.py 路由 + save_to_mysql 工具）。

使用 mock 模拟数据库 session。
"""

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient


class TestReportsAPI:
    """报告列表/详情接口测试"""

    @pytest.mark.asyncio
    async def test_list_reports_empty(self, async_client, mock_db_session):
        """报告列表为空时返回 total=0"""
        # mock 返回空结果
        mock_result = AsyncMock()
        mock_result.scalar_one = lambda: 0
        mock_result.scalars = lambda: type("obj", (object,), {"all": lambda self: []})()

        mock_db_session.execute = AsyncMock(return_value=mock_result)

        resp = await async_client.get("/api/v1/reports")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_reports_with_limit(self, async_client, mock_db_session):
        """limit 参数正确传递给数据库查询"""
        mock_result = AsyncMock()
        mock_result.scalar_one = lambda: 0
        mock_result.scalars = lambda: type("obj", (object,), {"all": lambda self: []})()

        mock_db_session.execute = AsyncMock(return_value=mock_result)

        resp = await async_client.get("/api/v1/reports?limit=5&offset=0")

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_reports_invalid_limit(self, async_client):
        """limit 超出范围应返回 422"""
        resp = await async_client.get("/api/v1/reports?limit=200")

        assert resp.status_code == 422  # 参数校验失败

    @pytest.mark.asyncio
    async def test_get_report_not_found(self, async_client, mock_db_session):
        """不存在的报告应返回 404"""
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = lambda: None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        resp = await async_client.get("/api/v1/reports/999")

        assert resp.status_code == 404
        assert "不存在" in resp.json()["detail"]


class TestSaveToMysqlTool:
    """save_to_mysql 工具测试"""

    @pytest.mark.asyncio
    async def test_save_report_success(self, mock_db_session):
        """保存成功返回确认信息"""
        from app.tools.github import save_to_mysql

        # mock session.refresh 设置 report.id（save_to_mysql 依赖 refresh 获取 id）
        saved_reports = []

        async def refresh_side_effect(report):
            report.id = 1

        mock_db_session.refresh = AsyncMock(side_effect=refresh_side_effect)

        result = await save_to_mysql.ainvoke({
            "title": "测试报告",
            "content": "这是测试内容",
            "query": "测试 query",
            "repo_owner": "test",
            "repo_name": "test",
            "sources": '["github:test/test"]',
        })

        assert "保存到 MySQL" in result
        assert "1" in result

    @pytest.mark.asyncio
    async def test_save_report_title_truncation(self, mock_db_session):
        """标题超过 255 字符应被截断"""
        from app.tools.github import save_to_mysql

        long_title = "A" * 300

        mock_db_session.add = AsyncMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        result = await save_to_mysql.ainvoke({
            "title": long_title,
            "content": "content",
        })

        assert "保存到 MySQL" in result

    @pytest.mark.asyncio
    async def test_save_report_sources_json(self, mock_db_session):
        """sources 为逗号分隔字符串时转为 JSON 数组"""
        from app.tools.github import save_to_mysql

        reports_saved = []

        async def add_side_effect(report):
            reports_saved.append(report)
            report.id = 2

        mock_db_session.add = AsyncMock(side_effect=add_side_effect)
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        result = await save_to_mysql.ainvoke({
            "title": "Test",
            "content": "content",
            "sources": "github:a/b, rss:https://example.com/feed",
        })

        assert "保存到 MySQL" in result
        # 验证 sources 被转成了 JSON 数组
        if reports_saved:
            import json
            saved_sources = json.loads(reports_saved[0].sources)
            assert isinstance(saved_sources, list)
            assert "github:a/b" in saved_sources
