"""
RSS 工具测试（fetch_rss_feed）。

使用 mock 模拟 HTTP 请求，不依赖真实 RSS 源。
"""

from unittest.mock import AsyncMock

import httpx
import pytest


# 模拟一段简单的 RSS XML 内容
SAMPLE_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Tech Blog</title>
    <item>
      <title>Python 3.13 Released</title>
      <link>https://example.com/python-313</link>
      <description>New features in Python 3.13 including the JIT compiler.</description>
      <pubDate>Mon, 15 Jan 2025 10:00:00 GMT</pubDate>
    </item>
    <item>
      <title>FastAPI 0.115 Update</title>
      <link>https://example.com/fastapi-0115</link>
      <description>Performance improvements and new features.</description>
      <pubDate>Fri, 10 Jan 2025 08:30:00 GMT</pubDate>
    </item>
    <item>
      <title>Docker Best Practices 2025</title>
      <link>https://example.com/docker-2025</link>
      <description>How to optimize your Docker images for production.</description>
      <pubDate>Wed, 08 Jan 2025 14:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

# 模拟空 RSS（无条目）
EMPTY_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Empty Blog</title>
  </channel>
</rss>
"""

# 模拟 Atom 格式
SAMPLE_ATOM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Blog</title>
  <entry>
    <title>Atom Entry 1</title>
    <link href="https://example.com/atom1"/>
    <summary type="text">Summary of atom entry 1</summary>
    <updated>2025-01-15T10:00:00Z</updated>
  </entry>
</feed>
"""


class TestFetchRssFeed:
    """RSS 订阅工具测试"""

    @pytest.mark.asyncio
    async def test_fetch_rss_returns_entries(self, monkeypatch):
        """
        正常 RSS 源应返回格式化后的文章列表。
        """
        # mock HTTP 请求返回 RSS XML
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_RSS_XML
        mock_response.raise_for_status = lambda: None

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.get = AsyncMock(return_value=mock_response)

        monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: mock_client)

        from app.tools.rss import fetch_rss_feed

        result = await fetch_rss_feed.ainvoke(
            {"feed_url": "https://example.com/rss", "max_entries": 10}
        )

        assert "Tech Blog" in result
        assert "Python 3.13 Released" in result
        assert "FastAPI 0.115 Update" in result
        assert "Docker Best Practices" in result
        assert "example.com" in result

    @pytest.mark.asyncio
    async def test_fetch_rss_empty_feed(self, monkeypatch):
        """空 RSS（无文章条目）应返回提示信息"""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = EMPTY_RSS_XML
        mock_response.raise_for_status = lambda: None

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.get = AsyncMock(return_value=mock_response)

        monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: mock_client)

        from app.tools.rss import fetch_rss_feed

        result = await fetch_rss_feed.ainvoke(
            {"feed_url": "https://example.com/empty", "max_entries": 10}
        )

        assert "Empty Blog" in result
        assert "未解析到文章" in result

    @pytest.mark.asyncio
    async def test_fetch_rss_http_error(self, monkeypatch):
        """HTTP 错误时应返回友好的错误信息"""
        from app.tools.rss import _fetch_feed_xml

        # 模拟 _fetch_feed_xml 直接抛出异常
        async def mock_fetch(url):
            raise httpx.HTTPStatusError(
                "Not Found",
                request=httpx.Request("GET", url),
                response=httpx.Response(404),
            )

        monkeypatch.setattr("app.tools.rss._fetch_feed_xml", mock_fetch)

        from app.tools.rss import fetch_rss_feed

        result = await fetch_rss_feed.ainvoke(
            {"feed_url": "https://example.com/bad-url", "max_entries": 10}
        )

        assert "无法获取 RSS 源" in result
        assert "404" in result

    @pytest.mark.asyncio
    async def test_fetch_rss_max_entries_limit(self, monkeypatch):
        """max_entries 应被限制在 1~20 范围内"""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        # 制造 25 条条目
        items = ""
        for i in range(25):
            items += f"""
            <item>
                <title>Article {i}</title>
                <link>https://example.com/{i}</link>
                <description>Description {i}</description>
            </item>
            """
        many_items_xml = f"""<?xml version="1.0"?>
        <rss version="2.0">
          <channel>
            <title>Many Items</title>
            {items}
          </channel>
        </rss>
        """
        mock_response.text = many_items_xml

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.get = AsyncMock(return_value=mock_response)

        monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: mock_client)

        from app.tools.rss import fetch_rss_feed

        # max_entries=100 → 会被 clamp 到 20
        result = await fetch_rss_feed.ainvoke(
            {"feed_url": "https://example.com/many", "max_entries": 100}
        )

        # 应只包含 20 条（最大限制）
        article_count = result.count("Article ")
        assert article_count == 20

    @pytest.mark.asyncio
    async def test_fetch_atom_feed(self, monkeypatch):
        """Atom 格式也能正常解析"""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_ATOM_XML
        mock_response.raise_for_status = lambda: None

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.get = AsyncMock(return_value=mock_response)

        monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: mock_client)

        from app.tools.rss import fetch_rss_feed

        result = await fetch_rss_feed.ainvoke(
            {"feed_url": "https://example.com/atom", "max_entries": 5}
        )

        assert "Atom Blog" in result
        assert "Atom Entry 1" in result

    @pytest.mark.asyncio
    async def test_fetch_rss_with_long_summary(self, monkeypatch):
        """超长摘要（>500 字符）应被截断"""
        long_summary = "A" * 1000
        long_rss = f"""<?xml version="1.0"?>
        <rss version="2.0">
          <channel>
            <title>Long Summary Blog</title>
            <item>
                <title>Long Article</title>
                <link>https://example.com/long</link>
                <description>{long_summary}</description>
            </item>
          </channel>
        </rss>
        """

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = long_rss
        mock_response.raise_for_status = lambda: None

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.get = AsyncMock(return_value=mock_response)

        monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: mock_client)

        from app.tools.rss import fetch_rss_feed

        result = await fetch_rss_feed.ainvoke(
            {"feed_url": "https://example.com/long", "max_entries": 1}
        )

        # 摘要应被截断到 500 字符 + "..."
        assert "..." in result
        # 不应该包含完整的 1000 个 A
        assert "A" * 600 not in result
