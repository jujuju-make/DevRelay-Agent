"""
聊天记忆服务测试（chat_memory.py）。

测试 Redis 聊天历史的读写操作。
"""

from unittest.mock import AsyncMock, patch

import pytest


class TestGetChatHistory:
    """获取聊天历史实例"""

    def test_get_chat_history_returns_instance(self, monkeypatch):
        """返回 DevRelayRedisChatMessageHistory 实例"""
        from app.services.chat_memory import get_chat_history, DevRelayRedisChatMessageHistory

        # mock Redis 连接
        monkeypatch.setattr(
            "langchain_community.chat_message_histories.RedisChatMessageHistory.__init__",
            lambda self, **kwargs: None,
        )

        history = get_chat_history("test-session")
        assert isinstance(history, DevRelayRedisChatMessageHistory)


class TestSaveChatTurn:
    """保存聊天记录"""

    def test_save_chat_turn_calls_add_message(self, monkeypatch):
        """调用 save_chat_turn 应保存用户消息和 AI 回复"""
        from app.services.chat_memory import save_chat_turn

        # mock get_chat_history 返回的对象
        mock_history = AsyncMock()
        mock_history.add_message = AsyncMock()
        monkeypatch.setattr(
            "app.services.chat_memory.get_chat_history",
            lambda session_id: mock_history,
        )

        save_chat_turn("test-session", "用户问题", "AI 回答")

        assert mock_history.add_message.call_count == 2


class TestLoadChatMessages:
    """加载聊天历史"""

    def test_load_chat_messages_returns_list(self, monkeypatch):
        """返回消息列表"""
        from app.services.chat_memory import load_chat_messages

        # mock messages 属性
        mock_history = AsyncMock()
        mock_history.messages = ["msg1", "msg2"]
        monkeypatch.setattr(
            "app.services.chat_memory.get_chat_history",
            lambda session_id: mock_history,
        )

        messages = load_chat_messages("test-session")
        assert list(messages) == ["msg1", "msg2"]

    def test_load_chat_messages_empty(self, monkeypatch):
        """无历史记录时返回空列表"""
        from app.services.chat_memory import load_chat_messages

        mock_history = AsyncMock()
        mock_history.messages = []
        monkeypatch.setattr(
            "app.services.chat_memory.get_chat_history",
            lambda session_id: mock_history,
        )

        messages = load_chat_messages("new-session")
        assert list(messages) == []
