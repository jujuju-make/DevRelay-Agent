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


class ArchiveDecisionRequest(BaseModel):
    """用户对归档询问的回应。"""

    session_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="会话 ID",
    )
    decision: str = Field(
        ...,
        pattern=r"^(accept|reject)$",
        description="归档决策：accept 确认保存，reject 放弃",
    )


class AgentRunResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)
    session_id: str
    pending_archive: bool = Field(
        default=False,
        description="Agent 是否在等待归档确认。前端据此显示 accept/reject 按钮。",
    )
