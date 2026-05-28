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

    注意：title 参数会被自动替换为 AI 生成的内容总结，你传什么都会被覆盖。

    Args:
        title: （会被自动覆盖）随意传即可
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

    # ── 用 LLM 自动生成标题摘要 ──
    auto_title = await _generate_digest_title(content, query, repo_owner, repo_name)
    if not auto_title:
        auto_title = title[:255]  # fallback 到 AI 传的

    # 最终检查：如果标题以开场白开头，直接从 content 取第一行
    bad_prefixes = ("好的", "以下是", "这次", "当然", "我来", "让我", "下面", "关于")
    if auto_title.startswith(bad_prefixes) or auto_title.strip() == "":
        # 取 content 第一行（去掉 # 标题行），最多 60 字
        first_line = content.split("\n")[0].lstrip("#").strip()
        if len(first_line) > 60:
            first_line = first_line[:57] + "..."
        auto_title = first_line if first_line else title[:255]

    try:
        factory = get_session_factory()
        async with factory() as session:
            report = Report(
                title=auto_title[:255],
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


async def _generate_digest_title(
    content: str,
    query: str = "",
    repo_owner: str = "",
    repo_name: str = "",
) -> str:
    """用 LLM 根据报告内容生成一句精炼的标题（10~30 字）。"""
    settings = get_settings()
    if not settings.openai_api_key:
        return ""

    repo_hint = f"（仓库 {repo_owner}/{repo_name}）" if repo_owner and repo_name else ""
    query_hint = f"用户问题：{query}" if query else ""

    # 取 content 前 1000 字做摘要
    content_sample = content[:1000]

    try:
        llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base,
            model=settings.openai_model,
            temperature=0.3,
        )
        resp = await llm.ainvoke(
            f"为以下内容生成一个归档标题。\n"
            f"规则：只用一句话概括核心内容，10~30字。禁止以「好的」「以下是」「关于」「报告」「分析」「总结」「让我」「我来」「这次」「当然」「下面」开头。直接输出标题本身，不要加引号。\n\n"
            f"{repo_hint} {query_hint}\n\n"
            f"内容：\n{content_sample}"
        )
        title = resp.content.strip() if resp.content else ""
        # 清理可能的引号
        title = title.strip('"').strip("'").strip("「").strip("」")
        return title[:255]
    except Exception:
        return ""


async def get_github_updates(owner: str, repo: str) -> str:
    """Agent 辅助：获取指定仓库最新 5 条 commit 的格式化字符串。"""
    return await fetch_repo_commits_tool.ainvoke(
        {"owner": owner, "repo": repo, "per_page": 5}
    )


async def fetch_commit_diff(
    owner: str,
    repo: str,
    commit_sha: str,
) -> dict[str, Any]:
    """
    获取某个 commit 的详细 diff（patch 格式）和文件变更列表。

    Returns:
        包含 sha, message, files (每个文件有 filename, status, patch, additions, deletions) 的 dict
    """
    settings = get_settings()
    url = f"{settings.github_api_base}/repos/{owner}/{repo}/commits/{commit_sha}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=_github_headers())
        response.raise_for_status()
        data = response.json()

    commit_data = data.get("commit", {})
    files = data.get("files", [])

    result: dict[str, Any] = {
        "sha": data.get("sha", commit_sha)[:7],
        "message": commit_data.get("message", "").split("\n")[0],
        "author": commit_data.get("author", {}).get("name", "Unknown"),
        "date": commit_data.get("author", {}).get("date", "")[:10],
        "total_changes": {
            "additions": data.get("stats", {}).get("additions", 0),
            "deletions": data.get("stats", {}).get("deletions", 0),
            "total": data.get("stats", {}).get("total", 0),
        },
        "files": [],
    }

    for f in files[:20]:  # 最多返回 20 个文件
        file_info = {
            "filename": f.get("filename", ""),
            "status": f.get("status", "modified"),  # added, modified, removed
            "additions": f.get("additions", 0),
            "deletions": f.get("deletions", 0),
            "changes": f.get("changes", 0),
            "patch": f.get("patch", ""),
        }
        result["files"].append(file_info)

    return result


def _format_diff_for_review(diff_data: dict[str, Any]) -> str:
    """将 diff 数据格式化为便于 AI 审查的文本形式。"""
    lines = [
        f"## Commit {diff_data['sha']} by {diff_data['author']} ({diff_data['date']})",
        f"**Message**: {diff_data['message']}",
        f"**Changes**: +{diff_data['total_changes']['additions']} / -{diff_data['total_changes']['deletions']} / {diff_data['total_changes']['total']} files changed",
        "",
    ]

    for f in diff_data["files"]:
        status_icon = {"added": "🆕", "modified": "📝", "removed": "🗑️"}.get(
            f["status"], "📄"
        )
        lines.append(
            f"### {status_icon} {f['filename']} ({f['status']}, +{f['additions']}/-{f['deletions']})"
        )
        if f.get("patch"):
            # patch 有长度限制，防止工具返回太长
            patch = f["patch"]
            max_patch_len = 4000
            if len(patch) > max_patch_len:
                patch = patch[:max_patch_len] + "\n...(diff 截断)"
            lines.append(f"```diff\n{patch}\n```")
        lines.append("")

    return "\n".join(lines)


@tool
async def review_commit_diff(owner: str, repo: str, commit_sha: str) -> str:
    """
    获取 GitHub 仓库某个 commit 的完整 diff 内容（具体修改了哪些行代码）。

    当你需要分析某次 commit 的具体代码变更时使用此工具，例如：
    - 用户问「这个 commit 改了哪些底层逻辑？」
    - 想了解某次改动的代码影响范围
    - 需要审查是否有安全隐患（如 SQL 注入、敏感信息泄露）

    **注意**：工具只返回原始 diff 数据，你需要根据返回的代码变化自行分析：
    - 是否修改了核心业务逻辑
    - 是否修改了 Pydantic Model / 数据库 Schema
    - 是否引入了安全风险（SQL 注入、硬编码密钥等）
    - 变更是否合理

    Args:
        owner: GitHub 用户名或组织名，例如 fastapi
        repo: 仓库名，例如 fastapi
        commit_sha: commit 的完整 SHA（40 位）或短 SHA（7 位）
    """
    try:
        diff_data = await fetch_commit_diff(owner, repo, commit_sha)
        return _format_diff_for_review(diff_data)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"⚠️ 未找到 commit `{commit_sha[:7]}` 在仓库 `{owner}/{repo}` 中，请检查 SHA 是否正确。"
        return _format_github_error(owner, repo, e.response.status_code)
    except httpx.RequestError as e:
        return f"⚠️ 无法连接到 GitHub API：{e}"
    except Exception as e:
        return f"⚠️ 获取 commit diff 时发生未知错误：{e}"


if __name__ == "__main__":
    import asyncio

    async def main() -> None:
        print("=== fetch_repo_commits_tool ===")
        commits_summary = await fetch_repo_commits_tool.ainvoke(
            {"owner": "fastapi", "repo": "fastapi", "per_page": 5}
        )
        print(commits_summary)

        print("\n=== review_commit_diff ===")
        diff = await review_commit_diff.ainvoke(
            {"owner": "fastapi", "repo": "fastapi", "commit_sha": "HEAD"}
        )
        print(diff)

    asyncio.run(main())
