from datetime import datetime

from pydantic import BaseModel, Field


class ReportSummary(BaseModel):
    id: int
    title: str
    query: str | None = None
    repo_owner: str | None = None
    repo_name: str | None = None
    sub_type: str | None = None
    created_at: datetime


class ReportDetail(ReportSummary):
    content: str
    sources: str | None = None


class ReportListResponse(BaseModel):
    total: int
    items: list[ReportSummary] = Field(default_factory=list)
