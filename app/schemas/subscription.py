from datetime import datetime

from pydantic import BaseModel, Field


class SubscriptionCreate(BaseModel):
    repo_owner: str = Field(..., min_length=1, max_length=128, description="GitHub 仓库 owner")
    repo_name: str = Field(..., min_length=1, max_length=128, description="GitHub 仓库 name")
    extra_sources: list[str] = Field(default_factory=list, description="额外 RSS 链接")


class SubscriptionUpdate(BaseModel):
    repo_owner: str | None = None
    repo_name: str | None = None
    extra_sources: list[str] | None = None
    active: bool | None = None


class SubscriptionResponse(BaseModel):
    id: int
    repo_owner: str
    repo_name: str
    extra_sources: list[str] = Field(default_factory=list)
    active: bool
    created_at: datetime
    updated_at: datetime


class SubscriptionListResponse(BaseModel):
    total: int
    items: list[SubscriptionResponse] = Field(default_factory=list)
