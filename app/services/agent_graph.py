"""
Agent wrapper with automatic archive suggestion.

流程：
1. 调用原有的 run_agent（使用 LangChain ReAct）
2. 从返回结果判断内容是否够多（>=50字 且有 sources）
3. 如果够多，把待归档内容存到 Redis（同步操作，线程安全）
4. 返回 pending_archive = true，前端显示归档按钮
5. 用户点击后 POST /archive-decision，从 Redis 读取并保存到 MySQL
"""

import asyncio
import json
import re

import redis as sync_redis

from app.config import get_settings
from app.database import get_session_factory
from app.models.report import Report
from app.services.agent_logic import run_agent as _original_run_agent

PENDING_KEY_PREFIX = "devrelay:pending_archive:"


# ── 同步 Redis 操作（用 asyncio.to_thread 避免事件循环问题）──

def _save_pending_sync(session_id: str, data: dict) -> None:
    try:
        settings = get_settings()
        r = sync_redis.from_url(settings.redis_url)
        key = f"{PENDING_KEY_PREFIX}{session_id}"
        r.setex(key, 600, json.dumps(data, ensure_ascii=False))
        r.close()
    except Exception:
        pass


def _load_pending_sync(session_id: str) -> dict | None:
    try:
        settings = get_settings()
        r = sync_redis.from_url(settings.redis_url)
        key = f"{PENDING_KEY_PREFIX}{session_id}"
        raw = r.get(key)
        r.close()
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return None


def _clear_pending_sync(session_id: str) -> None:
    try:
        settings = get_settings()
        r = sync_redis.from_url(settings.redis_url)
        key = f"{PENDING_KEY_PREFIX}{session_id}"
        r.delete(key)
        r.close()
    except Exception:
        pass


async def _save_pending(session_id: str, data: dict) -> None:
    await asyncio.to_thread(_save_pending_sync, session_id, data)


async def _load_pending(session_id: str) -> dict | None:
    return await asyncio.to_thread(_load_pending_sync, session_id)


async def _clear_pending(session_id: str) -> None:
    await asyncio.to_thread(_clear_pending_sync, session_id)


# ── Public API ──

async def run_agent_with_archive(
    query: str,
    *,
    session_id: str,
    repo_owner: str | None = None,
    repo_name: str | None = None,
) -> dict:
    """
    调用原有的 ReAct Agent，然后判断是否提示归档。
    """
    result = await _original_run_agent(
        query,
        session_id=session_id,
        repo_owner=repo_owner,
        repo_name=repo_name,
    )

    answer = result.get("answer", "")
    sources = result.get("sources", [])

    # 判断是否值得归档：内容 >= 50 字且有来源
    has_content = len(answer.strip()) >= 50
    has_sources = len(sources) > 0
    pending_archive = has_content and has_sources

    if pending_archive:
        # 提取标题（第一行）
        title = answer.strip().split("\n")[0].replace("#", "").strip()[:200]
        if not title:
            title = "技术报告"

        await _save_pending(session_id, {
            "title": title,
            "content": answer,
            "sources": sources,
        })

    return {
        "answer": answer,
        "sources": sources,
        "session_id": session_id,
        "pending_archive": pending_archive,
    }


async def handle_archive_response(
    session_id: str,
    decision: str,
) -> dict:
    """处理归档决策：accept → 保存到 MySQL，reject → 丢弃。"""
    if decision != "accept":
        await _clear_pending(session_id)
        return {
            "answer": "好的，已放弃归档。如有需要随时告诉我。",
            "session_id": session_id,
            "pending_archive": False,
        }

    pending = await _load_pending(session_id)
    if not pending or not pending.get("content"):
        return {
            "answer": "没有找到待归档的内容（可能已过期，最多保留 10 分钟）。请重新询问 Agent。",
            "session_id": session_id,
            "pending_archive": False,
        }

    try:
        title = pending["title"][:255]
        content = pending["content"]
        sources = pending.get("sources", [])

        # 从 sources 提取 repo 信息
        repo_owner = ""
        repo_name = ""
        for src in sources:
            m = re.match(r"github:(.+)/(.+)", src)
            if m:
                repo_owner = m.group(1)
                repo_name = m.group(2)

        sources_json = json.dumps(sources, ensure_ascii=False)

        factory = get_session_factory()
        async with factory() as session:
            report = Report(
                title=title,
                content=content,
                repo_owner=repo_owner or None,
                repo_name=repo_name or None,
                sources=sources_json or None,
                sub_type="manual",
            )
            session.add(report)
            await session.commit()
            await session.refresh(report)
            report_id = report.id

        await _clear_pending(session_id)

        return {
            "answer": f"报告已归档保存！ID: **{report_id}**，可在「GitHub 监控」中查看。",
            "session_id": session_id,
            "pending_archive": False,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "answer": f"归档失败: {e}",
            "session_id": session_id,
            "pending_archive": False,
        }
