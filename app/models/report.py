from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Report(Base):
    """Agent 生成的技术报告归档。"""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="报告标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="报告正文")
    query: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="用户原始问题")
    repo_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    repo_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sources: Mapped[str | None] = mapped_column(Text, nullable=True, comment="来源 JSON 字符串")
    sub_type: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="子类型: auto_digest / manual")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )
