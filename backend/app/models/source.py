from uuid import UUID, uuid4
from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.base import Base


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    group_id: Mapped[UUID] = mapped_column(ForeignKey("threat_groups.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_page: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_crawled_at: Mapped[str | None] = mapped_column(String(40))
    last_status: Mapped[str] = mapped_column(String(30), default="unknown", nullable=False)
