from uuid import UUID, uuid4
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.base import Base


class ThreatGroup(Base):
    __tablename__ = "threat_groups"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    parser_key: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    actor_type: Mapped[str] = mapped_column(String(80), default="Ransomware", nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    aliases: Mapped[str | None] = mapped_column(Text)
    first_observed_at: Mapped[str | None] = mapped_column(String(30))
    discovery_date: Mapped[str | None] = mapped_column(String(30))
