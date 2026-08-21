from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.base import Base


class VictimEnrichment(Base):
    __tablename__ = "victim_enrichments"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    victim_id: Mapped[UUID] = mapped_column(ForeignKey("victims.id", ondelete="CASCADE"), index=True, nullable=False)
    field_name: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    confidence: Mapped[float] = mapped_column(default=0.0, nullable=False)
    evidence_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
