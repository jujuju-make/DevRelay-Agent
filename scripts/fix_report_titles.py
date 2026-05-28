"""
批量修复历史报告的 title 字段。
对于每个 content 非空的报告，用 LLM 生成一句精炼总结作为新标题。
"""

import asyncio
import sys
from pathlib import Path

# 解决 app 导入路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_openai import ChatOpenAI
from sqlalchemy import select

from app.config import get_settings
from app.database import get_session_factory
from app.models.report import Report


async def _generate_title(content: str) -> str:
    """用 LLM 根据报告内容生成一句精炼标题（10~30 字）。"""
    settings = get_settings()
    if not settings.openai_api_key:
        return ""
    try:
        llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base,
            model=settings.openai_model,
            temperature=0.3,
        )
        resp = await llm.ainvoke(
            f"请根据以下报告内容，用一句话精炼总结作为归档标题（10~30 字）。\n"
            f"要求：不要用「报告」「分析」「总结」等词汇开头，直接概括核心内容。\n\n"
            f"报告内容：\n{content[:1000]}"
        )
        title = resp.content.strip() if resp.content else ""
        title = title.strip('"').strip("'").strip("「").strip("」")
        return title[:255]
    except Exception as e:
        print(f"  LLM 生成失败: {e}")
        return ""


async def main():
    settings = get_settings()
    factory = get_session_factory()

    async with factory() as session:
        result = await session.execute(
            select(Report).where(Report.content.isnot(None)).where(Report.content != "")
            .order_by(Report.id)
        )
        reports = result.scalars().all()

    print(f"共 {len(reports)} 条报告需要检查")

    fixed = 0
    for i, report in enumerate(reports):
        old_title = report.title or "(空)"
        # 跳过看起来已经正常的标题（含仓库名 + 非开场白）
        if old_title and not old_title.startswith(("好的", "以下是", "这次")):
            continue

        print(f"[{i+1}/{len(reports)}] ID={report.id} 旧标题: {old_title[:50]}")

        # 取 content 前 800 字作为总结素材
        content_sample = (report.content or "")[:800]
        if not content_sample.strip():
            print(f"  → 内容为空，跳过")
            continue

        new_title = await _generate_title(content_sample)
        if not new_title:
            print(f"  → 生成失败，保持原样")
            continue

        async with factory() as session:
            r = await session.get(Report, report.id)
            if r:
                r.title = new_title
                await session.commit()
                fixed += 1
                print(f"  ✓ 已更新为: {new_title}")

    print(f"\n完成！共修复 {fixed} 条报告的标题。")


if __name__ == "__main__":
    asyncio.run(main())
