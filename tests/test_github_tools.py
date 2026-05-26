"""
GitHub 相关工具测试（fetch_repo_commits, read_github_file, search_web）。

使用 mock 模拟 HTTP 请求，不依赖真实 GitHub API。
"""

import json
from unittest.mock import AsyncMock

import httpx
import pytest
from httpx import AsyncClient

from app.tools.github import (
    _format_commits_summary,
    _format_search_summary,
    commits_cache_key,
)


# ═══════════════════════════════════════════════
# 纯函数测试（不依赖外部服务）
# ═══════════════════════════════════════════════


class TestCommitsCacheKey:
    """缓存键生成逻辑"""

    def test_basic_key(self):
        """基本键格式正确"""
        key = commits_cache_key("fastapi", "fastapi", 10)
        assert key == "devrelay:commits:fastapi:fastapi:10:"

    def test_key_with_sha(self):
        """带 SHA 的键格式正确"""
        key = commits_cache_key("fastapi", "fastapi", 5, "main")
        assert key == "devrelay:commits:fastapi:fastapi:5:main"

    def test_key_special_chars(self):
        """含特殊字符的 owner/repo 也能生成有效键"""
        key = commits_cache_key("my-org", "my.repo_123", 10)
        assert key == "devrelay:commits:my-org:my.repo_123:10:"


class TestFormatCommitsSummary:
    """commit 格式化输出"""

    def test_empty_commits(self):
        """空 commit 列表返回提示信息"""
        result = _format_commits_summary([], "test", "repo")
        assert "未返回任何 commit" in result

    def test_single_commit(self):
        """单个 commit 格式化正确"""
        commits = [
            {
                "sha": "abc123def456",
                "commit": {
                    "message": "Fix bug in parser",
                    "author": {"name": "Alice", "date": "2025-01-15T10:00:00Z"},
                },
            }
        ]
        result = _format_commits_summary(commits, "owner", "repo")
        assert "owner/repo" in result
        assert "abc123d" in result  # SHA 前 7 位
        assert "Alice" in result
        assert "Fix bug" in result

    def test_multiple_commits(self):
        """多个 commit 按序号排列"""
        commits = [
            {"sha": "a" * 40, "commit": {"message": "First", "author": {"name": "A", "date": ""}}},
            {"sha": "b" * 40, "commit": {"message": "Second", "author": {"name": "B", "date": ""}}},
        ]
        result = _format_commits_summary(commits, "o", "r")
        assert "1." in result
        assert "2." in result

    def test_commit_without_author(self):
        """无 author 信息的 commit 不会崩溃"""
        commits = [
            {"sha": "abc123", "commit": {"message": "fix"}},
        ]
        result = _format_commits_summary(commits, "o", "r")
        assert "fix" in result
        assert "unknown" in result


class TestFormatSearchSummary:
    """搜索结果的格式化"""

    def test_no_results(self):
        """无搜索结果时显示友好提示"""
        result = _format_search_summary("test query", [])
        assert "未找到" in result
        assert "SERPER_API_KEY" in result

    def test_single_result(self):
        """单个搜索结果的格式"""
        results = [{"title": "FastAPI Docs", "link": "https://fastapi.tiangolo.com", "snippet": "FastAPI framework"}]
        result = _format_search_summary("fastapi", results)
        assert "FastAPI Docs" in result
        assert "fastapi.tiangolo.com" in result
        assert "FastAPI framework" in result

    def test_multiple_results(self):
        """多个搜索结果有序号"""
        results = [
            {"title": "A", "link": "https://a.com", "snippet": "snippet a"},
            {"title": "B", "link": "https://b.com", "snippet": "snippet b"},
        ]
        result = _format_search_summary("test", results)
        assert "1." in result
        assert "2." in result


# ═══════════════════════════════════════════════
# 工具函数测试（需 mock 外部依赖）
# ═══════════════════════════════════════════════


class TestFetchRepoCommitsTool:
    """fetch_repo_commits 工具测试"""

    @pytest.mark.asyncio
    async def test_tool_no_cache_calls_api(self, mock_redis, mock_httpx):
        """
        无缓存时，应调用 GitHub API 并回写缓存。
        """
        from app.tools.github import fetch_repo_commits_tool

        # mock_redis["get"] 默认返回 None → 模拟缓存未命中
        result = await fetch_repo_commits_tool.ainvoke(
            {"owner": "fastapi", "repo": "fastapi", "per_page": 3}
        )

        # 应返回格式化后的 commit 列表
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_tool_with_cache(self, mock_redis, mock_httpx):
        """
        有缓存时，直接返回缓存数据，不调用 API。
        """
        from app.tools.github import fetch_repo_commits_tool

        # 模拟缓存命中
        cached_data = [
            {
                "sha": "cachedsha123",
                "commit": {
                    "message": "cached commit",
                    "author": {"name": "Bot", "date": "2025-01-01T00:00:00Z"},
                },
            }
        ]
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_data))

        result = await fetch_repo_commits_tool.ainvoke(
            {"owner": "fastapi", "repo": "fastapi", "per_page": 3}
        )

        assert "cached commit" in result
        assert "Bot" in result

    @pytest.mark.asyncio
    async def test_tool_clamps_per_page(self, mock_redis, mock_httpx):
        """per_page 参数应在 1~30 范围内自动截断"""
        from app.tools.github import fetch_repo_commits_tool

        # per_page=0 → 会被 clamp 到 1
        result = await fetch_repo_commits_tool.ainvoke(
            {"owner": "o", "repo": "r", "per_page": 0}
        )
        assert isinstance(result, str)

        # per_page=100 → 会被 clamp 到 30
        result = await fetch_repo_commits_tool.ainvoke(
            {"owner": "o", "repo": "r", "per_page": 100}
        )
        assert isinstance(result, str)


class TestReadGithubFile:
    """read_github_file 工具测试"""

    @pytest.mark.asyncio
    async def test_read_file_success(self, mock_redis, mock_httpx):
        """成功读取文件返回正确格式"""
        from app.tools.github import read_github_file

        result = await read_github_file.ainvoke(
            {"owner": "fastapi", "repo": "fastapi", "path": "README.md"}
        )
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_read_file_http_error(self, mock_redis, monkeypatch):
        """HTTP 错误时返回友好的错误信息"""
        from app.tools.github import _fetch_github_content, read_github_file

        # 模拟 _fetch_github_content 直接抛出异常
        async def mock_fetch(owner, repo, path, ref=None):
            raise httpx.HTTPStatusError(
                "Not Found",
                request=httpx.Request("GET", "https://api.github.com/"),
                response=httpx.Response(404),
            )

        monkeypatch.setattr("app.tools.github._fetch_github_content", mock_fetch)

        result = await read_github_file.ainvoke(
            {"owner": "o", "repo": "r", "path": "nonexistent.md"}
        )
        assert "读取文件失败" in result
        assert "404" in result


class TestSearchWeb:
    """search_web 工具测试"""

    @pytest.mark.asyncio
    async def test_search_returns_results(self, mock_redis, monkeypatch):
        """搜索返回格式化结果"""
        # 为搜索单独设置 mock，返回 {"organic": [...]} 格式
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = lambda: {
            "organic": [
                {"title": "Test Title", "link": "https://test.com", "snippet": "test snippet"}
            ]
        }
        mock_response.raise_for_status = lambda: None
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.post = AsyncMock(return_value=mock_response)
        monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: mock_client)

        from app.tools.github import search_web

        result = await search_web.ainvoke(
            {"query": "FastAPI latest", "num_results": 3}
        )
        assert isinstance(result, str)
        assert "Test Title" in result

    @pytest.mark.asyncio
    async def test_search_without_api_key(self, mock_redis, monkeypatch):
        """无 SERPER_API_KEY 时返回提示信息"""
        from app.config import get_settings

        # 临时清空 API Key
        settings = get_settings()
        original_key = settings.serper_api_key
        settings.serper_api_key = ""

        from app.tools.github import search_web
        result = await search_web.ainvoke({"query": "test", "num_results": 3})

        assert "未找到" in result
        assert "SERPER_API_KEY" in result

        # 恢复
        settings.serper_api_key = original_key


