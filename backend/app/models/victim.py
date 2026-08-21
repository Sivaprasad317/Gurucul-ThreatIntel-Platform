from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.base import Base


class Victim(Base):
    __tablename__ = "victims"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True, nullable=False)
    group_id: Mapped[UUID] = mapped_column(ForeignKey("threat_groups.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(500), index=True, nullable=False)
    domain: Mapped[str | None] = mapped_column(String(500))
    country_code: Mapped[str | None] = mapped_column(String(2), index=True)
    country_name: Mapped[str | None] = mapped_column(String(120))
    industry_code: Mapped[str | None] = mapped_column(String(80), index=True)
    industry_name: Mapped[str | None] = mapped_column(String(160))
    country_source: Mapped[str | None] = mapped_column(String(120))
    industry_source: Mapped[str | None] = mapped_column(String(120))
    country_confidence: Mapped[float | None]
    industry_confidence: Mapped[float | None]
    country_evidence: Mapped[str | None] = mapped_column(Text)
    industry_evidence: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    published_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    discovered_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    source_page: Mapped[str] = mapped_column(Text, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

Index("ix_victims_group_normalized_name", Victim.group_id, Victim.normalized_name, unique=True)
