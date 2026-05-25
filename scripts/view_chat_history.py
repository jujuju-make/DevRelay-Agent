"""在终端以中文打印 Redis 中的会话记录。用法: python scripts/view_chat_history.py <session_id>"""

import json
import sys

import redis

from app.config import get_settings


def main() -> None:
    session_id = sys.argv[1] if len(sys.argv) > 1 else "test-session-devrelay"
    settings = get_settings()
    key = f"{settings.chat_history_key_prefix}{session_id}"

    client = redis.from_url(settings.redis_url, decode_responses=True)
    items = client.lrange(key, 0, -1)
    if not items:
        print(f"未找到会话: {key}")
        return

    print(f"Key: {key}\n")
    for raw in reversed(items):
        msg = json.loads(raw)
        role = "用户" if msg.get("type") == "human" else "AI"
        content = msg.get("data", {}).get("content", "")
        print(f"--- {role} ---")
        print(content)
        print()


if __name__ == "__main__":
    main()
