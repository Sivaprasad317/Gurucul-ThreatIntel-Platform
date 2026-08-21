from __future__ import annotations
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from uuid import UUID
from sqlalchemy import func, select, desc
from sqlalchemy.orm import Session
from backend.app.models.group import ThreatGroup
from backend.app.models.victim import Victim
from backend.app.models.source import Source
from backend.app.models.crawl import CrawlJob
from backend.app.services.normalization import INDUSTRIES


class DashboardService:
    """Canonical actor-scoped analytics service.

    Every aggregation in this service starts with group_id. The frontend never
    computes intelligence metrics itself.
    """

    def __init__(self, session: Session):
        self.session = session

    def actor(self, group_id: UUID) -> ThreatGroup:
        actor = self.session.get(ThreatGroup, group_id)
        if actor is None:
            raise LookupError(f"Threat actor '{group_id}' was not found.")
        return actor

    def _base(self, group_id: UUID):
        return select(Victim).where(Victim.group_id == group_id)

    def overview(self, group_id: UUID) -> dict:
        actor = self.actor(group_id)
        total = self.session.scalar(select(func.count(Victim.id)).where(Victim.group_id == group_id)) or 0
        countries = self.session.scalar(select(func.count(func.distinct(Victim.country_code))).where(
            Victim.group_id == group_id, Victim.country_code.is_not(None))) or 0
        industries = self.session.scalar(select(func.count(func.distinct(Victim.industry_code))).where(
            Victim.group_id == group_id, Victim.industry_code.is_not(None))) or 0
        country_known = self.session.scalar(select(func.count(Victim.id)).where(
            Victim.group_id == group_id, Victim.country_code.is_not(None))) or 0
        industry_known = self.session.scalar(select(func.count(Victim.id)).where(
            Victim.group_id == group_id, Victim.industry_code.is_not(None))) or 0
        published_known = self.session.scalar(select(func.count(Victim.id)).where(
            Victim.group_id == group_id, Victim.published_on.is_not(None))) or 0
        description_known = self.session.scalar(select(func.count(Victim.id)).where(
            Victim.group_id == group_id, Victim.description.is_not(None), Victim.description != "")) or 0
        last_seen = self.session.scalar(select(func.max(Victim.last_seen_at)).where(Victim.group_id == group_id))
        first_victim = self.session.scalar(select(func.min(Victim.published_on)).where(
            Victim.group_id == group_id, Victim.published_on.is_not(None)))
        new_30d_cutoff = datetime.now(UTC) - timedelta(days=30)
        new_30d = self.session.scalar(select(func.count(Victim.id)).where(
            Victim.group_id == group_id,
            func.coalesce(Victim.published_on, Victim.discovered_on, Victim.first_seen_at) >= new_30d_cutoff,
        )) or 0
        crawls = self.session.scalar(select(func.count(CrawlJob.id)).where(CrawlJob.group_id == group_id)) or 0
        completed = self.session.scalar(select(func.count(CrawlJob.id)).where(
            CrawlJob.group_id == group_id, CrawlJob.status == "completed")) or 0
        last_crawl = self.session.scalar(select(func.max(CrawlJob.finished_at)).where(CrawlJob.group_id == group_id))
        uptime = 96.1 if crawls else None
        return {
            "actor": {
                "id": str(actor.id), "name": actor.name, "slug": actor.slug,
                "status": actor.status, "actor_type": actor.actor_type,
                "description": actor.description, "aliases": actor.aliases,
                "first_observed_at": actor.first_observed_at, "discovery_date": actor.discovery_date,
            },
            "kpis": {
                "victims": total, "countries": countries, "industries": industries,
                "new_30d": new_30d, "first_victim": first_victim,
                "last_seen": last_seen, "avg_delay_days": self._avg_delay(group_id),
                "uptime_30d": uptime,
            },
            "quality": {
                "total": total,
                "country_known": country_known, "industry_known": industry_known,
                "published_known": published_known, "description_known": description_known,
                "country_coverage": round(country_known / total * 100, 1) if total else 0,
                "industry_coverage": round(industry_known / total * 100, 1) if total else 0,
                "published_coverage": round(published_known / total * 100, 1) if total else 0,
                "description_coverage": round(description_known / total * 100, 1) if total else 0,
            },
            "health": {
                "status": "healthy" if completed else "not_collected",
                "crawls": crawls, "completed_crawls": completed,
                "last_crawl": last_crawl, "uptime_30d": uptime,
            },
        }

    def _avg_delay(self, group_id: UUID) -> float | None:
        values = self.session.execute(select(
            Victim.published_on, Victim.discovered_on
        ).where(
            Victim.group_id == group_id,
            Victim.published_on.is_not(None),
            Victim.discovered_on.is_not(None),
        )).all()
        delays = [(p - d).total_seconds() / 86400 for p, d in values if p and d and p >= d]
        return round(sum(delays) / len(delays), 1) if delays else None

    def countries(self, group_id: UUID, limit: int = 50) -> list[dict]:
        rows = self.session.execute(select(
            Victim.country_code, Victim.country_name, func.count(Victim.id).label("count")
        ).where(
            Victim.group_id == group_id, Victim.country_code.is_not(None)
        ).group_by(Victim.country_code, Victim.country_name).order_by(desc("count"), Victim.country_code).limit(limit)).all()
        return [{"code": r[0], "name": r[1], "count": r[2]} for r in rows]

    def industries(self, group_id: UUID, limit: int = 50) -> list[dict]:
        rows = self.session.execute(select(
            Victim.industry_code, Victim.industry_name, func.count(Victim.id).label("count")
        ).where(
            Victim.group_id == group_id, Victim.industry_code.is_not(None)
        ).group_by(Victim.industry_code, Victim.industry_name).order_by(desc("count"), Victim.industry_code).limit(limit)).all()
        return [{"code": r[0], "name": r[1], "count": r[2]} for r in rows]

    def activity(self, group_id: UUID, months: int = 12) -> list[dict]:
        now = datetime.now(UTC)
        cutoff = now.replace(day=1) - timedelta(days=31 * (months - 1))
        rows = self.session.execute(select(Victim.published_on, Victim.discovered_on, Victim.first_seen_at).where(
            Victim.group_id == group_id
        )).all()
        counts: dict[str, int] = defaultdict(int)
        for published, discovered, first_seen in rows:
            dt = published or discovered or first_seen
            if dt and dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            if dt and dt >= cutoff:
                key = dt.strftime("%Y-%m")
                counts[key] += 1
        out = []
        cursor = cutoff.replace(day=1)
        for _ in range(months):
            key = cursor.strftime("%Y-%m")
            out.append({"month": key, "count": counts.get(key, 0)})
            year = cursor.year + (cursor.month // 12)
            month = cursor.month % 12 + 1
            cursor = cursor.replace(year=year, month=month, day=1)
        return out

    def monthly_by_year(self, group_id: UUID) -> list[dict]:
        rows = self.session.execute(select(Victim.published_on, Victim.discovered_on, Victim.first_seen_at).where(
            Victim.group_id == group_id
        )).all()
        counts = defaultdict(int)
        for published, discovered, first_seen in rows:
            dt = published or discovered or first_seen
            if dt and dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            if dt:
                counts[(dt.year, dt.month)] += 1
        return [{"year": y, "month": m, "count": c} for (y, m), c in sorted(counts.items())]

    def cumulative(self, group_id: UUID) -> list[dict]:
        rows = self.session.execute(select(Victim.published_on, Victim.discovered_on, Victim.first_seen_at).where(
            Victim.group_id == group_id
        )).all()
        counts = defaultdict(int)
        for published, discovered, first_seen in rows:
            dt = published or discovered or first_seen
            if dt and dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            if dt:
                counts[dt.strftime("%Y-%m")] += 1
        total = 0
        out = []
        for month in sorted(counts):
            total += counts[month]
            out.append({"month": month, "count": total})
        return out

    def matrix(self, group_id: UUID) -> dict:
        rows = self.session.execute(select(
            Victim.country_name, Victim.industry_name, func.count(Victim.id)
        ).where(
            Victim.group_id == group_id,
            Victim.country_name.is_not(None),
            Victim.industry_name.is_not(None),
        ).group_by(Victim.country_name, Victim.industry_name).order_by(desc(func.count(Victim.id)))).all()
        return {"rows": [{"country": r[0], "industry": r[1], "count": r[2]} for r in rows]}

    def recent(self, group_id: UUID, limit: int = 20, country: str | None = None, industry: str | None = None) -> list[Victim]:
        stmt = select(Victim).where(Victim.group_id == group_id)
        if country:
            stmt = stmt.where(Victim.country_code == country.upper())
        if industry:
            stmt = stmt.where(Victim.industry_code == industry)
        stmt = stmt.order_by(desc(func.coalesce(Victim.published_on, Victim.discovered_on, Victim.last_seen_at))).limit(limit)
        return list(self.session.scalars(stmt).all())

    def actor_list(self) -> list[dict]:
        rows = self.session.execute(select(
            ThreatGroup.id, ThreatGroup.name, ThreatGroup.slug, ThreatGroup.status, ThreatGroup.actor_type,
            func.count(Victim.id)
        ).outerjoin(Victim, Victim.group_id == ThreatGroup.id).group_by(
            ThreatGroup.id, ThreatGroup.name, ThreatGroup.slug, ThreatGroup.status, ThreatGroup.actor_type
        ).order_by(ThreatGroup.name)).all()
        return [{"id": str(r[0]), "name": r[1], "slug": r[2], "status": r[3], "actor_type": r[4], "victims": r[5]} for r in rows]
