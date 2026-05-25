from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    app: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentRunRequest(BaseModel):
    """触发 Agent 编排时的请求体。"""

    query: str = Field(..., min_length=1, description="用户或调度器下发的任务描述")
    session_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="会话 ID，用于 Redis 聊天记忆隔离",
    )
    repo_owner: str | None = Field(None, description="GitHub 仓库所有者")
    repo_name: str | None = Field(None, description="GitHub 仓库名称")


class AgentRunResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)
    session_id: str
