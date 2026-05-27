"""
Daily Digest — 自动日报服务。

流程：
1. 每天定时从 MySQL 读取所有 active 的 subscriptions（或指定单个 sub_id）
2. 对每个仓库，抓取 commits
3. 调用 LLM 对 commits 做 AI 总结
4. 将结果保存到 reports 表
5. （未来可扩展）推送到钉钉/飞书/企业微信
"""

import json
from datetime import datetime

from langchain_openai import ChatOpenAI
from sqlalchemy import select

from app.config import get_settings
from app.database import get_session_factory
from app.models.report import Report
from app.models.subscription import Subscription
from app.tools.github import fetch_repo_commits


async def _ai_summarize(owner: str, repo: str, commits: list[dict]) -> str:
    """用 LLM 对 commits 做一句话总结。"""
    if not commits:
        return ""

    settings = get_settings()
    if not settings.openai_api_key:
        return ""

    # 构建 commit 消息摘要
    lines = []
    for c in commits:
        sha = c.get("sha", "")[:7]
        msg = c.get("commit", {}).get("message", "").split("\n")[0]
        author = c.get("commit", {}).get("author", {}).get("name", "Unknown")
        lines.append(f"- {sha}: {msg} (by {author})")
    commits_text = "\n".join(lines)

    try:
        llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base,
            model=settings.openai_model,
            temperature=0.3,
        )
        resp = await llm.ainvoke(
            f"请用一句话总结 {owner}/{repo} 最近的 Git 提交趋势和主要内容：\n\n{commits_text}\n\n用中文回答，不超过 50 字。"
        )
        summary = resp.content.strip() if resp.content else ""
        return summary
    except Exception:
        return ""


async def _build_digest_for_sub(sub: Subscription) -> dict:
    """为单个订阅生成日报并保存。"""
    today = datetime.now().strftime("%Y-%m-%d")
    title = f"[自动日报] {sub.repo_owner}/{sub.repo_name} — {today}"

    # 1. 抓取 commits
    commits = await fetch_repo_commits(
        owner=sub.repo_owner,
        repo=sub.repo_name,
        per_page=10,
    )

    # 2. 构建内容
    content_parts = [f"# {title}\n"]

    # AI 总结
    summary = await _ai_summarize(sub.repo_owner, sub.repo_name, commits)
    if summary:
        content_parts.append(f"> 🤖 **AI 概览**：{summary}\n")

    if commits:
        content_parts.append("## 📦 最新提交\n")
        for c in commits:
            sha = c.get("sha", "")[:7]
            msg = c.get("commit", {}).get("message", "").split("\n")[0]
            author = c.get("commit", {}).get("author", {}).get("name", "Unknown")
            date = c.get("commit", {}).get("author", {}).get("date", "")[:10]
            content_parts.append(f"- `{sha}` {msg} — {author} ({date})")
    else:
        content_parts.append("*近 24 小时无新提交。*\n")

    content = "\n".join(content_parts)

    # 3. 来源
    sources_json = ""
    extra_sources = []
    if sub.extra_sources:
        try:
            extra_sources = json.loads(sub.extra_sources)
        except (json.JSONDecodeError, TypeError):
            extra_sources = []

    source_items = [f"github:{sub.repo_owner}/{sub.repo_name}"]
    for src in extra_sources:
        source_items.append(f"rss:{src}")

        sources_json = json.dumps(source_items, ensure_ascii=False)

    # 4. 保存
    factory = get_session_factory()
    async with factory() as session:
        report = Report(
            title=title[:255],
            content=content,
            query=f"每日自动订阅 — {sub.repo_owner}/{sub.repo_name}",
            repo_owner=sub.repo_owner,
            repo_name=sub.repo_name,
            sources=sources_json,
            sub_type="auto_digest",
        )
        session.add(report)
        await session.commit()
        await session.refresh(report)
        report_id = report.id

    return {
        "title": title,
        "sub_id": sub.id,
        "report_id": report_id,
        "repo": f"{sub.repo_owner}/{sub.repo_name}",
    }


async def generate_daily_digest(sub_id: int | None = None) -> list[dict]:
    """
    生成日报。

    Args:
        sub_id: 如果指定，只为该订阅生成；否则为所有 active 订阅生成。

    Returns:
        生成的报告列表
    """
    factory = get_session_factory()

    if sub_id is not None:
        async with factory() as session:
            result = await session.execute(
                select(Subscription).where(Subscription.id == sub_id)
            )
            sub = result.scalar_one_or_none()
        if sub is None:
            return [{"title": "订阅不存在", "sub_id": sub_id, "report_id": None, "error": f"订阅 {sub_id} 不存在"}]
        if not sub.active:
            return [{"title": "订阅已暂停", "sub_id": sub_id, "report_id": None, "error": f"订阅 {sub_id} 未启用"}]
        subs = [sub]
    else:
        async with factory() as session:
            result = await session.execute(
                select(Subscription).where(Subscription.active == True)  # noqa: E712
            )
            subs = result.scalars().all()

    if not subs:
        return []

    generated = []
    for sub in subs:
        try:
            result = await _build_digest_for_sub(sub)
            generated.append(result)
        except Exception as e:
            import traceback
            traceback.print_exc()
            generated.append({
                "title": f"[日报失败] {sub.repo_owner}/{sub.repo_name}",
                "sub_id": sub.id,
                "report_id": None,
                "error": str(e),
            })

    return generated
