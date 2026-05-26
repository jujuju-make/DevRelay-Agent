"""
Agent 编排逻辑测试（agent_logic.py）。

包括：
- 纯函数测试：_build_user_message、_extract_final_answer、_extract_sources
- 集成测试：run_agent（mock LLM）
"""

from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


# ═══════════════════════════════════════════════
# 纯函数测试
# ═══════════════════════════════════════════════


class TestBuildUserMessage:
    """用户消息构建逻辑"""

    def test_basic_query(self):
        """纯 query 时不追加上下文提示"""
        from app.services.agent_logic import _build_user_message

        result = _build_user_message("你好")
        assert result == "你好"
        assert "[上下文提示]" not in result

    def test_with_repo_context(self):
        """带 repo 信息时追加上下文提示"""
        from app.services.agent_logic import _build_user_message

        result = _build_user_message(
            "最近有什么更新",
            repo_owner="fastapi",
            repo_name="fastapi",
        )
        assert "最近有什么更新" in result
        assert "fastapi" in result
        assert "上下文提示" in result

    def test_with_partial_repo(self):
        """只提供 owner 或 repo 时不追加上下文"""
        from app.services.agent_logic import _build_user_message

        result = _build_user_message("test", repo_owner="owner", repo_name=None)
        assert "[上下文提示]" not in result

        result2 = _build_user_message("test", repo_owner=None, repo_name="repo")
        assert "[上下文提示]" not in result2


class TestExtractFinalAnswer:
    """从消息列表中提取最终回答"""

    def _tool_call(self, name: str, **kwargs):
        """创建符合 langchain 格式的 tool_call 字典"""
        import uuid
        return {"name": name, "args": kwargs, "id": str(uuid.uuid4())[:8]}

    def test_extract_aimessage_text(self):
        """优先提取最后一个无 tool_calls 的 AIMessage"""
        from app.services.agent_logic import _extract_final_answer

        messages = [
            HumanMessage(content="你好"),
            AIMessage(content="我是中间消息", tool_calls=[self._tool_call("test")]),
            AIMessage(content="这是最终回答"),
        ]
        result = _extract_final_answer(messages)
        assert result == "这是最终回答"

    def test_extract_with_empty_content(self):
        """跳过 content 为空的 AIMessage"""
        from app.services.agent_logic import _extract_final_answer

        messages = [
            AIMessage(content=""),
            AIMessage(content="真实回答"),
        ]
        result = _extract_final_answer(messages)
        assert result == "真实回答"

    def test_extract_fallback_to_any_aimessage(self):
        """如果没有符合条件的消息，退而求其次取最后一个 AIMessage"""
        from app.services.agent_logic import _extract_final_answer

        messages = [
            AIMessage(content="只有这一条", tool_calls=[self._tool_call("test")]),
        ]
        result = _extract_final_answer(messages)
        assert result == "只有这一条"  # fallback

    def test_extract_no_aimessage(self):
        """没有 AIMessage 时返回默认提示"""
        from app.services.agent_logic import _extract_final_answer

        messages = [HumanMessage(content="hi")]
        result = _extract_final_answer(messages)
        assert "未生成有效回答" in result

    def test_extract_aimessage_with_text_list(self):
        """处理 content 为 list 格式的消息（多模态场景）"""
        from app.services.agent_logic import _extract_final_answer

        messages = [
            AIMessage(
                content=[
                    {"type": "text", "text": "第一段 "},
                    {"type": "text", "text": "第二段"},
                ]
            ),
        ]
        result = _extract_final_answer(messages)
        assert result == "第一段 第二段"


class TestExtractSources:
    """从消息列表中提取来源"""

    def _tool_call(self, name: str, **kwargs):
        import uuid
        return {"name": name, "args": kwargs, "id": str(uuid.uuid4())[:8]}

    def test_extract_github_commit_source(self):
        """从 tool_calls 中提取 GitHub 来源"""
        from app.services.agent_logic import _extract_sources

        messages = [
            AIMessage(
                content="",
                tool_calls=[self._tool_call("fetch_repo_commits", owner="fastapi", repo="fastapi")],
            ),
        ]
        sources = _extract_sources(messages)
        assert "github:fastapi/fastapi" in sources

    def test_extract_rss_source(self):
        """从 tool_calls 中提取 RSS 来源"""
        from app.services.agent_logic import _extract_sources

        messages = [
            AIMessage(
                content="",
                tool_calls=[self._tool_call("fetch_rss_feed", feed_url="https://example.com/rss")],
            ),
        ]
        sources = _extract_sources(messages)
        assert "rss:https://example.com/rss" in sources

    def test_extract_search_source(self):
        """从 tool_calls 中提取搜索来源"""
        from app.services.agent_logic import _extract_sources

        messages = [
            AIMessage(
                content="",
                tool_calls=[self._tool_call("search_web", query="FastAPI 0.115")],
            ),
        ]
        sources = _extract_sources(messages)
        assert "search:FastAPI 0.115" in sources

    def test_extract_urls_from_tool_message(self):
        """从 ToolMessage 中提取 URL"""
        from app.services.agent_logic import _extract_sources

        messages = [
            ToolMessage(
                content='参考链接: https://fastapi.tiangolo.com 和 https://github.com/fastapi/fastapi',
                tool_call_id="1",
            ),
        ]
        sources = _extract_sources(messages)
        assert "https://fastapi.tiangolo.com" in sources
        assert "https://github.com/fastapi/fastapi" in sources

    def test_extract_deduplicates(self):
        """相同来源不会被重复添加"""
        from app.services.agent_logic import _extract_sources

        messages = [
            AIMessage(
                content="",
                tool_calls=[self._tool_call("fetch_repo_commits", owner="fastapi", repo="fastapi")],
            ),
            AIMessage(
                content="",
                tool_calls=[self._tool_call("fetch_repo_commits", owner="fastapi", repo="fastapi")],
            ),
        ]
        sources = _extract_sources(messages)
        # 只出现一次
        assert len([s for s in sources if s == "github:fastapi/fastapi"]) == 1


# ═══════════════════════════════════════════════
# run_agent 集成测试
# ═══════════════════════════════════════════════


class TestRunAgent:
    """run_agent 函数集成测试（mock LLM 调用）"""

    @pytest.mark.asyncio
    async def test_run_agent_no_api_key(self, monkeypatch):
        """未配置 API_KEY 时返回提示信息"""
        from app.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "openai_api_key", "")

        from app.services.agent_logic import run_agent

        result = await run_agent(
            "test query",
            session_id="test-session",
        )

        assert result["answer"] == "未配置 OPENAI_API_KEY，无法启动 ReAct Agent。"
        assert result["sources"] == []
        assert result["session_id"] == "test-session"

    @pytest.mark.asyncio
    async def test_run_agent_with_mock_llm(self, monkeypatch):
        """模拟 LLM 返回，验证 run_agent 的处理流程"""
        from app.services.agent_logic import run_agent

        # 模拟 agent.ainvoke 的返回值
        mock_messages = [
            HumanMessage(content="test query"),
            AIMessage(content="这是模拟的最终回答"),
        ]
        mock_result = {"messages": mock_messages}

        # mock _build_react_agent 返回一个 agent，其 ainvoke 返回 mock 结果
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(return_value=mock_result)

        monkeypatch.setattr(
            "app.services.agent_logic._build_react_agent",
            lambda: mock_agent,
        )
        # mock 聊天记忆的加载和保存
        monkeypatch.setattr(
            "app.services.agent_logic.load_chat_messages",
            lambda session_id: [],
        )
        monkeypatch.setattr(
            "app.services.agent_logic.save_chat_turn",
            lambda session_id, user_text, answer: None,
        )

        result = await run_agent(
            "test query",
            session_id="test-session",
            repo_owner="fastapi",
            repo_name="fastapi",
        )

        assert result["answer"] == "这是模拟的最终回答"
        assert result["session_id"] == "test-session"
