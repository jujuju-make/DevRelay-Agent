"""技术博客 RSS 订阅工具。"""

import asyncio
from typing import Any

import feedparser
import httpx
from langchain_core.tools import tool


async def _fetch_feed_xml(feed_url: str) -> str:
    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers={"User-Agent": "DevRelay-Agent/0.1"},
    ) as client:
        response = await client.get(feed_url)
        response.raise_for_status()
        return response.text


def _parse_feed(
    xml: str, feed_url: str, max_entries: int
) -> tuple[list[dict[str, Any]], str]:
    parsed = feedparser.parse(xml)
    entries: list[dict[str, Any]] = []
    for entry in parsed.entries[:max_entries]:
        published = entry.get("published") or entry.get("updated", "")
        summary = entry.get("summary", "") or entry.get("description", "")
        if summary and len(summary) > 500:
            summary = summary[:500] + "..."
        entries.append(
            {
                "title": entry.get("title", "无标题"),
                "link": entry.get("link", ""),
                "published": published,
                "summary": summary,
            }
        )
    feed_title = getattr(parsed.feed, "title", feed_url)
    return entries, feed_title


def _format_rss_summary(
    feed_url: str,
    feed_title: str,
    entries: list[dict[str, Any]],
) -> str:
    if not entries:
        return f"RSS 源「{feed_title}」({feed_url}) 未解析到文章条目，请检查 URL 是否为有效 RSS/Atom 地址。"

    lines = [f"## {feed_title}", f"源地址: {feed_url}", ""]
    for idx, item in enumerate(entries, 1):
        lines.append(
            f"{idx}. **{item['title']}**\n"
            f"   - 发布时间: {item['published'] or '未知'}\n"
            f"   - 链接: {item['link']}\n"
            f"   - 摘要: {item['summary'] or '无'}"
        )
    return "\n\n".join(lines)


@tool
async def fetch_rss_feed(feed_url: str, max_entries: int = 10) -> str:
    """
    抓取技术博客或资讯站的 RSS/Atom 订阅源，返回最近文章列表。

    适用于监控技术博客更新、框架官方博客、个人博客 RSS 等场景。
    常见 RSS 地址示例：博客首页 `/feed`、`/rss.xml`、`/atom.xml`。

    Args:
        feed_url: RSS/Atom 订阅链接（完整 URL）
        max_entries: 返回最近文章条数，默认 10，最大 20
    """
    max_entries = max(1, min(max_entries, 20))
    try:
        xml = await _fetch_feed_xml(feed_url)
        entries, feed_title = await asyncio.to_thread(
            _parse_feed, xml, feed_url, max_entries
        )
        return _format_rss_summary(feed_url, feed_title, entries)
    except httpx.HTTPStatusError as e:
        return f"无法获取 RSS 源（HTTP {e.response.status_code}）: {feed_url}"
    except Exception as e:
        return f"解析 RSS 失败: {e}"
