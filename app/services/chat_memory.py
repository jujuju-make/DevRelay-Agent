"""Redis 聊天记忆（RedisChatMessageHistory）。"""

import json

from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, message_to_dict

from app.config import get_settings


class DevRelayRedisChatMessageHistory(RedisChatMessageHistory):
    """写入 Redis 时保留中文原文（ensure_ascii=False），便于在 Redis Insight / CLI 中阅读。"""

    def add_message(self, message: BaseMessage) -> None:
        payload = json.dumps(message_to_dict(message), ensure_ascii=False)
        self.redis_client.lpush(self.key, payload)
        if self.ttl:
            self.redis_client.expire(self.key, self.ttl)


def get_chat_history(session_id: str) -> DevRelayRedisChatMessageHistory:
    """按 session_id 获取 Redis 聊天历史实例（TTL 24 小时）。"""
    settings = get_settings()
    return DevRelayRedisChatMessageHistory(
        session_id=session_id,
        url=settings.redis_url,
        key_prefix=settings.chat_history_key_prefix,
        ttl=settings.chat_history_ttl_seconds,
    )


def load_chat_messages(session_id: str) -> list:
    """从 Redis 加载该 session 的历史消息。"""
    return list(get_chat_history(session_id).messages)


def save_chat_turn(session_id: str, user_text: str, answer: str) -> None:
    """将本轮用户问题与 AI 最终回答写入 Redis，并刷新 24h TTL。"""
    history = get_chat_history(session_id)
    history.add_message(HumanMessage(content=user_text))
    history.add_message(AIMessage(content=answer))
