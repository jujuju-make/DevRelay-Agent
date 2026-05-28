"""LangChain ReAct Agent 编排逻辑。"""

import asyncio
import re

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI

from app.config import get_settings
from app.services.chat_memory import load_chat_messages, save_chat_turn
from app.tools import DEVRELAY_TOOLS

SYSTEM_PROMPT = """你是 DevRelay，一名帮助开发者追踪 GitHub 仓库动态与技术博客/资讯的助手。

请使用 ReAct 思路完成任务：先思考需要什么信息，再调用工具，根据工具返回继续推理，直到能给出完整回答。

工具使用策略：
1. 涉及某开源项目「最近更新、commit、改动」时，优先调用 fetch_repo_commits（需 owner 与 repo）。
2. 需要 README、文档或某源码文件内容时，调用 read_github_file（owner、repo、path，如 README.md）。
3. 用户给出博客/资讯 RSS 订阅链接，或要追踪技术博客更新时，调用 fetch_rss_feed（feed_url）。
4. 若上述信息不足（如版本说明、社区评价），再调用 search_web；对关键链接可用 read_web_page 读正文。
5. 当用户需要分析某次 commit 的底层逻辑改动时，调用 review_commit_diff（需 owner、repo、commit_sha）。
   review_commit_diff 返回的是原始 diff 代码，你需要自行分析并告知用户：
   - 是否修改了核心底层逻辑
   - 是否修改了 Pydantic Model 或数据库 Schema
   - 是否引入了潜在安全风险（SQL 注入、硬编码密钥等）
   - 变更的整体影响和合理性
6. 完成报告后，若质量较好，请在末尾友好询问是否保存到 MySQL；仅当用户明确同意后再调用 save_to_mysql。

回答要求：用中文、结构清晰；区分「仓库事实」「RSS/博客」「网上观点」；不要编造未在工具结果中出现的信息；结合历史对话理解追问与指代。"""


def _build_react_agent():
    settings = get_settings()
    llm = ChatOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_api_base,
        model=settings.openai_model,
        temperature=0.2,
    )
    return create_agent(
        model=llm,
        tools=DEVRELAY_TOOLS,
        system_prompt=SYSTEM_PROMPT,
    )


def _build_user_message(
    query: str,
    *,
    repo_owner: str | None = None,
    repo_name: str | None = None,
) -> str:
    parts = [query]
    if repo_owner and repo_name:
        parts.append(
            f"\n[上下文提示] 若问题与仓库相关，GitHub owner={repo_owner!r}, repo={repo_name!r}。"
        )
    return "".join(parts)


def _extract_final_answer(messages: list) -> str:
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
            text = msg.content
            if isinstance(text, str):
                return text.strip()
            if isinstance(text, list):
                chunks = [
                    block.get("text", "")
                    for block in text
                    if isinstance(block, dict) and block.get("type") == "text"
                ]
                return "".join(chunks).strip()
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            text = msg.content
            return text if isinstance(text, str) else str(text)
    return "Agent 未生成有效回答，请检查工具调用与模型配置。"


def _extract_sources(messages: list) -> list[str]:
    seen: set[str] = set()
    sources: list[str] = []

    def add(item: str) -> None:
        if item and item not in seen:
            seen.add(item)
            sources.append(item)

    for msg in messages:
        if isinstance(msg, AIMessage):
            for call in msg.tool_calls or []:
                name = call.get("name", "")
                args = call.get("args", {})
                if name == "fetch_repo_commits":
                    add(f"github:{args.get('owner')}/{args.get('repo')}")
                elif name == "read_github_file":
                    add(f"github-file:{args.get('owner')}/{args.get('repo')}/{args.get('path', '')}")
                elif name == "review_commit_diff":
                    add(f"github-diff:{args.get('owner')}/{args.get('repo')}@{args.get('commit_sha', '')[:7]}")
                elif name == "fetch_rss_feed":
                    add(f"rss:{args.get('feed_url', '')}")
                elif name == "search_web":
                    add(f"search:{args.get('query', '')}")
                elif name == "read_web_page":
                    add(str(args.get("url", "")))
                elif name == "save_to_mysql":
                    add(f"mysql:report:{args.get('title', '')}")
        if isinstance(msg, ToolMessage):
            for url in re.findall(r"https?://[^\s\)\]]+", str(msg.content)):
                add(url)

    return sources


async def run_agent(
    query: str,
    *,
    session_id: str,
    repo_owner: str | None = None,
    repo_name: str | None = None,
) -> dict[str, str | list[str]]:
    """
    使用 LangChain ReAct Agent 执行任务：模型自动选择并调用工具，循环推理后给出最终回答。

    运行前从 Redis（RedisChatMessageHistory）加载 session 历史；运行后将本轮问答写回 Redis（24h TTL）。

    Returns:
        包含 answer、sources 与 session_id 的字典
    """
    settings = get_settings()

    if not settings.openai_api_key:
        return {
            "answer": "未配置 OPENAI_API_KEY，无法启动 ReAct Agent。",
            "sources": [],
            "session_id": session_id,
        }

    history_messages = load_chat_messages(session_id)
    user_text = _build_user_message(
        query, repo_owner=repo_owner, repo_name=repo_name
    )
    user_message = HumanMessage(content=user_text)

    agent = _build_react_agent()
    result = await agent.ainvoke(
        {"messages": [*history_messages, user_message]},
    )
    messages = result.get("messages", [])

    answer = _extract_final_answer(messages)
    sources = _extract_sources(messages)

    save_chat_turn(session_id, user_text, answer)

    return {
        "answer": answer,
        "sources": sources,
        "session_id": session_id,
    }


async def _test_run_agent() -> None:
    session_id = "test-session-devrelay"
    query = "请查看我的仓库jujuju-make/Intelligent-news最近的动态"
    result = await run_agent(
        query,
        session_id=session_id,
        repo_owner="fastapi",
        repo_name="fastapi",
    )
    print("Session:", result.get("session_id"))
    print("Agent answer:")
    print(result.get("answer"))
    print("\nSources:", result.get("sources"))


if __name__ == "__main__":
    asyncio.run(_test_run_agent())
