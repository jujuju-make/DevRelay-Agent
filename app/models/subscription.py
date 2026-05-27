from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Subscription(Base):
    """用户关注的仓库/数据源订阅。"""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_owner: Mapped[str] = mapped_column(String(128), nullable=False, comment="GitHub 仓库 owner")
    repo_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="GitHub 仓库 name")
    # 额外数据源，如 RSS 链接，JSON 格式 ["https://blog.com/rss", ...]
    extra_sources: Mapped[str | None] = mapped_column(String(1024), nullable=True, comment="额外 RSS 链接，JSON 数组")
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否启用")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
