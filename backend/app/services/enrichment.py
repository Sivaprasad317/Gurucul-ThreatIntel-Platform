from __future__ import annotations
from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.models.victim import Victim
from backend.app.models.enrichment import VictimEnrichment
from backend.app.services.normalization import country_from_value, infer_country_from_domain, infer_industry, extract_domain


def enrich_victim(session: Session, victim: Victim) -> None:
    """Fill only missing country/industry values and record provenance."""
    domain = victim.domain or extract_domain(victim.source_page)
    if domain and not victim.domain:
        victim.domain = domain

    if not victim.country_code:
        code, name, confidence = country_from_value(victim.country_name)
        if code:
            victim.country_code, victim.country_name = code, name
            victim.country_source, victim.country_confidence = "source_normalization", confidence
            session.add(VictimEnrichment(victim_id=victim.id, field_name="country",
                                         value=name, source="source_normalization",
                                         confidence=confidence, evidence_url=victim.source_page))
        else:
            code, name, confidence = infer_country_from_domain(domain)
            if code:
                victim.country_code, victim.country_name = code, name
                victim.country_source, victim.country_confidence = "ccTLD_inference", confidence
                session.add(VictimEnrichment(victim_id=victim.id, field_name="country",
                                             value=name, source="ccTLD_inference",
                                             confidence=confidence, evidence_url=victim.source_page))

    if not victim.industry_code:
        code, name, confidence = infer_industry(" ".join(x for x in [victim.name, victim.description] if x))
        if code:
            victim.industry_code, victim.industry_name = code, name
            victim.industry_source, victim.industry_confidence = "keyword_inference", confidence
            session.add(VictimEnrichment(victim_id=victim.id, field_name="industry",
                                         value=name, source="keyword_inference",
                                         confidence=confidence, evidence_url=victim.source_page))


def enrich_group(session: Session, group_id) -> int:
    victims = session.scalars(select(Victim).where(Victim.group_id == group_id)).all()
    changed = 0
    for victim in victims:
        before = (victim.country_code, victim.industry_code)
        enrich_victim(session, victim)
        if before != (victim.country_code, victim.industry_code):
            changed += 1
    session.commit()
    return changed
