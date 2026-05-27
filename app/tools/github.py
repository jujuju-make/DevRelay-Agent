"""GitHub 与全网搜索相关的 LangChain 工具。"""

import base64
import json
from typing import Any

import httpx
from langchain_core.tools import tool

from app.config import get_settings
from app.database import get_session_factory
from app.models.report import Report
from app.services.cache import (
    commits_cache_key,
    get_cached_commits,
    set_cached_commits,
)
from app.tools.read_web_page import read_web_page


async def fetch_repo_commits(
    owner: str,
    repo: str,
    *,
    per_page: int = 10,
    sha: str | None = None,
) -> list[dict[str, Any]]:
    """
    异步抓取指定 GitHub 仓库的 Commit 列表（原始 JSON）。

    执行前优先读取 Redis 缓存（10 分钟 TTL）；未命中再请求 GitHub API 并回写缓存。
    """
    cache_key = commits_cache_key(owner, repo, per_page, sha)
    cached = await get_cached_commits(cache_key)
    if cached is not None:
        return cached

    settings = get_settings()
    url = f"{settings.github_api_base}/repos/{owner}/{repo}/commits"
    params: dict[str, Any] = {"per_page": per_page}
    if sha:
        params["sha"] = sha

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params, headers=_github_headers())
        response.raise_for_status()
        data: list[dict[str, Any]] = response.json()

    await set_cached_commits(cache_key, data)
    return data


def _format_github_error(owner: str, repo: str, status_code: int) -> str:
    """统一格式化 GitHub API 错误为友好提示。"""
    if status_code == 404:
        return f"⚠️ 未找到仓库 `{owner}/{repo}`，请检查用户名和仓库名是否正确。"
    if status_code == 403:
        return f"⚠️ 访问 `{owner}/{repo}` 被拒绝（403），可能是 API 速率限制或私有仓库。"
    if status_code == 401:
        return "⚠️ GitHub API 认证失败，请检查 GITHUB_TOKEN 是否有效。"
    return f"⚠️ 请求 `{owner}/{repo}` 时出错（HTTP {status_code}）"


def _format_commits_summary(commits: list[dict[str, Any]], owner: str, repo: str) -> str:
    if not commits:
        return f"仓库 {owner}/{repo} 未返回任何 commit。"

    lines = [f"## {owner}/{repo} 最近提交"]
    for idx, commit in enumerate(commits, 1):
        sha = commit.get("sha", "")[:7]
        message = (commit.get("commit") or {}).get("message", "").split("\n")[0]
        author = (commit.get("commit") or {}).get("author", {}).get("name", "unknown")
        date = (commit.get("commit") or {}).get("author", {}).get("date", "")
        lines.append(f"{idx}. [{sha}] {date} {author}: {message}")
    return "\n".join(lines)


async def _serper_search(query: str, *, num_results: int = 5) -> list[dict[str, str]]:
    settings = get_settings()
    if not settings.serper_api_key:
        return []

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": settings.serper_api_key,
                "Content-Type": "application/json",
            },
            json={"q": query, "num": num_results},
        )
        response.raise_for_status()
        data = response.json()

    results: list[dict[str, str]] = []
    for item in data.get("organic", [])[:num_results]:
        results.append(
            {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            }
        )
    return results


def _format_search_summary(query: str, results: list[dict[str, str]]) -> str:
    if not results:
        return (
            f"未找到与「{query}」相关的网页摘要。"
            "请配置 SERPER_API_KEY 后重试，或缩小/调整搜索关键词。"
        )

    lines = [f"## 全网搜索结果：{query}"]
    for idx, item in enumerate(results, 1):
        title = item.get("title", "无标题")
        link = item.get("link", "")
        snippet = item.get("snippet", "无摘要")
        lines.append(f"{idx}. **{title}**\n   - 链接: {link}\n   - 摘要: {snippet}")
    return "\n\n".join(lines)


@tool("fetch_repo_commits")
async def fetch_repo_commits_tool(
    owner: str,
    repo: str,
    per_page: int = 10,
) -> str:
    """
    从 GitHub 仓库获取最近的 commit 记录，返回便于阅读的文本摘要。

    适用于回答「某仓库最近更新了什么」「最新提交有哪些」等问题。

    Args:
        owner: GitHub 用户名或组织名，例如 fastapi
        repo: 仓库名，例如 fastapi
        per_page: 获取条数，默认 10，最大建议 30
    """
    per_page = max(1, min(per_page, 30))
    try:
        commits = await fetch_repo_commits(owner, repo, per_page=per_page)
    except httpx.HTTPStatusError as e:
        return _format_github_error(owner, repo, e.response.status_code)
    except httpx.RequestError as e:
        return f"⚠️ 无法连接到 GitHub API：{e}"
    except Exception as e:
        return f"⚠️ 获取 commit 时发生未知错误：{e}"

    return _format_commits_summary(commits, owner, repo)


def _github_headers() -> dict[str, str]:
    settings = get_settings()
    headers: dict[str, str] = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers


async def _fetch_github_content(
    owner: str,
    repo: str,
    path: str,
    *,
    ref: str | None = None,
) -> str:
    settings = get_settings()
    url = f"{settings.github_api_base}/repos/{owner}/{repo}/contents/{path.lstrip('/')}"
    params: dict[str, str] = {}
    if ref:
        params["ref"] = ref

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params, headers=_github_headers())
        response.raise_for_status()
        data = response.json()

    if isinstance(data, list):
        names = [item.get("name", "") for item in data[:30]]
        return (
            f"`{path}` 是目录，包含 {len(data)} 项。前 30 项：\n"
            + "\n".join(f"- {n}" for n in names)
        )

    if data.get("encoding") != "base64":
        return f"不支持的文件编码: {data.get('encoding')}"

    raw = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    max_chars = 8000
    if len(raw) > max_chars:
        return raw[:max_chars] + f"\n\n...(已截断，原文共 {len(raw)} 字符)"
    return raw


@tool
async def read_github_file(owner: str, repo: str, path: str, ref: str = "") -> str:
    """
    读取 GitHub 仓库中指定文件的内容（如 README.md、docs/xxx.md、配置文件等）。

    Args:
        owner: 仓库所有者
        repo: 仓库名
        path: 文件路径，例如 README.md 或 src/main.py
        ref: 可选分支名、tag 或 commit SHA，默认使用默认分支
    """
    try:
        content = await _fetch_github_content(owner, repo, path, ref=ref or None)
        return f"## {owner}/{repo}/{path}\n\n{content}"
    except httpx.HTTPStatusError as e:
        return _format_github_error(owner, repo, e.response.status_code)
    except httpx.RequestError as e:
        return f"⚠️ 无法连接到 GitHub API：{e}"
    except Exception as e:
        return f"⚠️ 读取文件时发生未知错误：{e}"


@tool
async def search_web(query: str, num_results: int = 5) -> str:
    """
    当 GitHub 上的信息不足以回答用户时，使用此工具在全网搜索最新的技术文章和评价。

    返回搜索到的网页标题、链接与摘要，供 Agent 综合回答。

    Args:
        query: 搜索关键词，建议包含技术名、版本或「评测」「教程」等词
        num_results: 返回结果条数，默认 5
    """
    num_results = max(1, min(num_results, 10))
    try:
        results = await _serper_search(query, num_results=num_results)
    except httpx.HTTPStatusError as e:
        return f"⚠️ 搜索服务异常（HTTP {e.response.status_code}），请稍后重试。"
    except httpx.RequestError as e:
        return f"⚠️ 无法连接到搜索服务：{e}"
    except Exception as e:
        return f"⚠️ 搜索时发生未知错误：{e}"
    return _format_search_summary(query, results)


@tool
async def save_to_mysql(
    title: str,
    content: str,
    query: str = "",
    repo_owner: str = "",
    repo_name: str = "",
    sources: str = "",
) -> str:
    """
    将 Agent 生成的技术报告保存到 MySQL 数据库归档。

    仅在用户明确表示希望保存报告时调用此工具。

    Args:
        title: 报告标题
        content: 报告正文（Markdown 或纯文本）
        query: 用户原始问题（可选）
        repo_owner: 相关 GitHub 仓库 owner（可选）
        repo_name: 相关 GitHub 仓库名（可选）
        sources: 来源列表，JSON 数组字符串或逗号分隔（可选）
    """
    sources_json = sources
    if sources and not sources.strip().startswith("["):
        parts = [s.strip() for s in sources.split(",") if s.strip()]
        sources_json = json.dumps(parts, ensure_ascii=False)

    try:
        factory = get_session_factory()
        async with factory() as session:
            report = Report(
                title=title[:255],
                content=content,
                query=query or None,
                repo_owner=repo_owner or None,
                repo_name=repo_name or None,
                sources=sources_json or None,
            )
            session.add(report)
            await session.commit()
            await session.refresh(report)
    except Exception as e:
        return f"⚠️ 保存报告到数据库失败：{e}"

    return f"报告已成功保存到 MySQL，归档 ID: {report.id}，标题: {report.title}"


async def get_github_updates(owner: str, repo: str) -> str:
    """Agent 辅助：获取指定仓库最新 5 条 commit 的格式化字符串。"""
    return await fetch_repo_commits_tool.ainvoke(
        {"owner": owner, "repo": repo, "per_page": 5}
    )


if __name__ == "__main__":
    import asyncio

    async def main() -> None:
        print("=== fetch_repo_commits_tool ===")
        commits_summary = await fetch_repo_commits_tool.ainvoke(
            {"owner": "fastapi", "repo": "fastapi", "per_page": 5}
        )
        print(commits_summary)
        print("\n=== search_web ===")
        web_summary = await search_web.ainvoke(
            {"query": "FastAPI 0.115 release notes review", "num_results": 3}
        )
        print(web_summary)

    asyncio.run(main())
