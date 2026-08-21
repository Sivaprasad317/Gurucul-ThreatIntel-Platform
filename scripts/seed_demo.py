from __future__ import annotations
from datetime import UTC, datetime, timedelta
from pathlib import Path
import random
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from backend.app.db.base import Base
from backend.app.db.session import SessionLocal, engine
from backend.app.models import Source, ThreatGroup, Victim
from backend.app.services.normalization import COUNTRIES, INDUSTRIES, normalize_name
from backend.app.services.bootstrap import ensure_admin
from backend.app.core.config import get_settings

random.seed(42)

COUNTRY_DIST = [("US", 0.49), ("GB", 0.08), ("DE", 0.07), ("CA", 0.05), ("IT", 0.04),
                ("AU", 0.035), ("FR", 0.035), ("IN", 0.03), ("CN", 0.025), ("NL", 0.02),
                ("ES", 0.02), ("BR", 0.02), ("SE", 0.015), ("JP", 0.015), ("SG", 0.01), ("ZA", 0.01)]
IND_DIST = [("professional-services", 0.24), ("manufacturing", 0.20), ("technology", 0.14),
            ("retail", 0.10), ("healthcare", 0.08), ("transportation", 0.07), ("financial-services", 0.06),
            ("construction", 0.04), ("hospitality", 0.03), ("energy", 0.02), ("telecommunications", 0.02)]

def weighted(items):
    r = random.random()
    total = 0
    for key, weight in items:
        total += weight
        if r <= total:
            return key
    return items[-1][0]

def ensure_actor(session, name, slug, parser, description, first, discovery, count):
    actor = session.scalar(select(ThreatGroup).where(ThreatGroup.slug == slug))
    if not actor:
        actor = ThreatGroup(name=name, slug=slug, parser_key=parser, status="active",
                            actor_type="Ransomware-as-a-Service", description=description,
                            aliases="", first_observed_at=first, discovery_date=discovery)
        session.add(actor); session.flush()
    source = session.scalar(select(Source).where(Source.group_id == actor.id))
    if not source:
        source = Source(group_id=actor.id, name="Demo intelligence source",
                        base_url=f"https://demo.invalid/group/{slug}",
                        source_page=f"https://demo.invalid/group/{slug}", enabled=True,
                        last_status="completed", last_crawled_at=datetime.now(UTC).isoformat())
        session.add(source); session.flush()
    existing = session.scalar(select(Victim.id).where(Victim.group_id == actor.id))
    if existing:
        return actor, 0
    start = datetime.now(UTC) - timedelta(days=1095)
    for i in range(count):
        country = weighted(COUNTRY_DIST)
        industry = weighted(IND_DIST)
        published = start + timedelta(days=random.randint(0, 1095), hours=random.randint(0, 23))
        discovered = published - timedelta(days=random.randint(0, 24))
        name = f"Demo {name} Victim {i+1:04d}"
        session.add(Victim(
            source_id=source.id, group_id=actor.id, name=name, normalized_name=normalize_name(name),
            domain=f"demo-{slug}-{i+1:04d}.invalid", country_code=country, country_name=COUNTRIES[country],
            industry_code=industry, industry_name=dict(INDUSTRIES)[industry],
            country_source="demo_dataset", industry_source="demo_dataset",
            country_confidence=1.0, industry_confidence=1.0,
            country_evidence="Synthetic demo record", industry_evidence="Synthetic demo record",
            description=f"Synthetic demo intelligence record for {name}. Replace demo data with live collection.",
            published_on=published, discovered_on=discovered,
            source_page=source.source_page, first_seen_at=discovered, last_seen_at=published
        ))
    return actor, count

def main():
    settings = get_settings()
    Base.metadata.create_all(bind=engine)
    if not settings.seed_demo_data:
        print("SEED_DEMO_DATA=false; no synthetic data inserted.")
        return
    with SessionLocal() as session:
        ensure_admin(session)
        ensure_actor(session, "DragonForce", "dragonforce", "dragonforce",
                     "Synthetic demo profile based on the actor-dashboard reference design.", "2023-08-01", "2023-12-13", 640)
        ensure_actor(session, "Qilin", "qilin", "qilin",
                     "Synthetic demo profile for actor-scoped analytics validation.", "2022-10-20", "2023-12-13", 1096)
        ensure_actor(session, "Black Basta", "blackbasta", "blackbasta",
                     "Synthetic demo profile for actor-scoped analytics validation.", "2022-02-01", "2022-04-01", 420)
        session.commit()
    print("Demo database ready. Synthetic records are labelled in the dashboard.")
if __name__ == "__main__":
    main()
