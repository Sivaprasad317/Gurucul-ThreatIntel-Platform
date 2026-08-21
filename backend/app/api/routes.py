from datetime import UTC, datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from backend.app.api.dependencies import require_auth
from backend.app.core.config import get_settings
from backend.app.core.security import create_access_token, verify_password
from backend.app.db.session import get_db
from backend.app.models import CrawlJob, Source, ThreatGroup, User, Victim
from backend.app.repositories.users import UserRepository
from backend.app.schemas.auth import LoginRequest, TokenResponse
from backend.app.schemas.dashboard import CrawlRead, VictimRead
from backend.app.schemas.groups import GroupCreate, SourceCreate
from backend.app.services.dashboard import DashboardService
from backend.app.services.enrichment import enrich_group
from backend.app.services.crawl import CrawlService
from backend.app.services.ransomware_live import RansomwareLiveClient

router = APIRouter(prefix="/api/v1")


def victim_read(v: Victim) -> dict:
    return {
        "id": str(v.id), "name": v.name, "country_code": v.country_code, "country_name": v.country_name,
        "industry_code": v.industry_code, "industry_name": v.industry_name, "description": v.description,
        "published_on": v.published_on, "discovered_on": v.discovered_on, "source_page": v.source_page,
        "first_seen_at": v.first_seen_at, "last_seen_at": v.last_seen_at,
    }


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = UserRepository(db).get_by_email(payload.email)
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    return TokenResponse(access_token=create_access_token(str(user.id), user.email))


@router.get("/health")
def health():
    return {"status": "ok", "time": datetime.now(UTC).isoformat()}


@router.get("/config", dependencies=[Depends(require_auth)])
def config():
    s = get_settings()
    return {"demo_mode": s.demo_mode, "live_api_configured": bool(s.ransomware_live_api_key and s.ransomware_live_group_endpoint)}


@router.get("/dashboard/actors", dependencies=[Depends(require_auth)])
def actors(db: Session = Depends(get_db)):
    return DashboardService(db).actor_list()


@router.get("/dashboard/{group_id}/overview", dependencies=[Depends(require_auth)])
def overview(group_id: UUID, db: Session = Depends(get_db)):
    try:
        return DashboardService(db).overview(group_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/dashboard/{group_id}/countries", dependencies=[Depends(require_auth)])
def countries(group_id: UUID, limit: int = Query(50, ge=1, le=100), db: Session = Depends(get_db)):
    return DashboardService(db).countries(group_id, limit)


@router.get("/dashboard/{group_id}/industries", dependencies=[Depends(require_auth)])
def industries(group_id: UUID, limit: int = Query(50, ge=1, le=100), db: Session = Depends(get_db)):
    return DashboardService(db).industries(group_id, limit)


@router.get("/dashboard/{group_id}/activity", dependencies=[Depends(require_auth)])
def activity(group_id: UUID, months: int = Query(12, ge=3, le=36), db: Session = Depends(get_db)):
    service = DashboardService(db)
    return {"velocity": service.activity(group_id, months), "monthly": service.monthly_by_year(group_id), "cumulative": service.cumulative(group_id)}


@router.get("/dashboard/{group_id}/matrix", dependencies=[Depends(require_auth)])
def matrix(group_id: UUID, db: Session = Depends(get_db)):
    return DashboardService(db).matrix(group_id)


@router.get("/dashboard/{group_id}/victims", dependencies=[Depends(require_auth)])
def victims(
    group_id: UUID, limit: int = Query(50, ge=1, le=200),
    country: str | None = None, industry: str | None = None,
    db: Session = Depends(get_db)
):
    return [victim_read(v) for v in DashboardService(db).recent(group_id, limit, country, industry)]


@router.post("/dashboard/{group_id}/enrich", dependencies=[Depends(require_auth)])
def enrich(group_id: UUID, db: Session = Depends(get_db)):
    return {"updated": enrich_group(db, group_id)}



@router.get("/extractors", dependencies=[Depends(require_auth)])
def extractors():
    from backend.app.extractors.registry import available_extractors
    return available_extractors()


@router.post("/groups", status_code=201, dependencies=[Depends(require_auth)])
def create_group(payload: GroupCreate, db: Session = Depends(get_db)):
    from backend.app.extractors.registry import available_extractors
    if payload.parser_key not in available_extractors():
        raise HTTPException(409, f"No installed parser for '{payload.parser_key}'.")
    existing = db.scalar(select(ThreatGroup).where((ThreatGroup.slug == payload.slug) | (ThreatGroup.name == payload.name)))
    if existing:
        raise HTTPException(409, "An actor with this name or slug already exists.")
    actor = ThreatGroup(
        name=payload.name.strip(), slug=payload.slug.strip().lower(), parser_key=payload.parser_key,
        actor_type=payload.actor_type, description=payload.description, aliases=payload.aliases,
        first_observed_at=payload.first_observed_at, discovery_date=payload.discovery_date,
    )
    db.add(actor); db.commit(); db.refresh(actor)
    return {"id": str(actor.id), "name": actor.name, "slug": actor.slug, "status": actor.status,
            "actor_type": actor.actor_type, "victims": 0}

@router.post("/sources", dependencies=[Depends(require_auth)])
def create_source(
    payload: SourceCreate,
    db: Session = Depends(get_db),
):
    group_id = UUID(payload.group_id)

    group = db.get(ThreatGroup, group_id)

    if group is None:
        raise HTTPException(
            status_code=404,
            detail="Threat actor not found.",
        )

    existing = db.scalar(
        select(Source).where(
            Source.group_id == group_id,
            Source.base_url == payload.base_url,
        )
    )

    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="Source with this URL already exists for this threat actor.",
        )

    source = Source(
        group_id=group_id,
        name=payload.name,
        base_url=payload.base_url,
        source_page=payload.source_page,
        enabled=payload.enabled,
        last_status="pending",
    )

    db.add(source)
    db.commit()
    db.refresh(source)

    return {
        "id": str(source.id),
        "group_id": str(source.group_id),
        "name": source.name,
        "base_url": source.base_url,
        "source_page": source.source_page,
        "enabled": source.enabled,
        "last_status": source.last_status,
    }

@router.get("/sources", dependencies=[Depends(require_auth)])
def sources(group_id: UUID | None = None, db: Session = Depends(get_db)):
    stmt = select(Source).order_by(Source.name)
    if group_id:
        stmt = stmt.where(Source.group_id == group_id)
    rows = db.scalars(stmt).all()
    return [{"id": str(s.id), "group_id": str(s.group_id), "name": s.name, "base_url": s.base_url,
             "source_page": s.source_page, "enabled": s.enabled, "last_status": s.last_status, "last_crawled_at": s.last_crawled_at} for s in rows]


@router.get("/crawls", dependencies=[Depends(require_auth)])
def crawls(group_id: UUID | None = None, limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    stmt = select(CrawlJob).order_by(desc(CrawlJob.created_at)).limit(limit)
    if group_id:
        stmt = stmt.where(CrawlJob.group_id == group_id)
    return [CrawlRead.model_validate(x, from_attributes=True).model_dump(mode="json") for x in db.scalars(stmt).all()]


@router.post("/sources/{source_id}/crawl", dependencies=[Depends(require_auth)])
def crawl(source_id: UUID, db: Session = Depends(get_db)):
    try:
        job = CrawlService(db).crawl(source_id)
        return {"id": str(job.id), "status": job.status, "victims_found": job.victims_found}
    except Exception as exc:
        raise HTTPException(502, f"Crawl failed: {exc}") from exc


@router.post("/integrations/ransomware-live/groups/{group_id}/sync", dependencies=[Depends(require_auth)])
def ransomware_live_sync(group_id: UUID, db: Session = Depends(get_db)):
    actor = db.get(ThreatGroup, group_id)
    if actor is None:
        raise HTTPException(404, "Threat actor not found.")
    client = RansomwareLiveClient()
    try:
        records = client.sync_payload(actor.slug)
    except Exception as exc:
        raise HTTPException(502, str(exc)) from exc
    source = db.scalar(select(Source).where(Source.group_id == group_id).order_by(Source.id))
    if source is None:
        source = Source(group_id=group_id, name="Ransomware.live API",
                        base_url=get_settings().ransomware_live_group_endpoint or "https://api-pro.ransomware.live",
                        source_page="https://www.ransomware.live/", enabled=True)
        db.add(source); db.flush()
    created = updated = 0
    service = CrawlService(db)
    candidates = []
    from backend.app.extractors.base import CandidateVictim
    for raw in records:
        item = client.normalize_record(raw)
        if not item["name"]:
            continue
        candidates.append(CandidateVictim(
            name=str(item["name"]), source_page=str(item["source_page"] or source.source_page),
            country=str(item["country"]) if item["country"] else None,
            industry=str(item["industry"]) if item["industry"] else None,
            description=str(item["description"]) if item["description"] else None,
            published_on=item["published_on"], discovered_on=item["discovered_on"],
            website=str(item["website"]) if item["website"] else None,
        ))
    before = db.scalar(select(func.count(Victim.id)).where(Victim.group_id == group_id)) or 0
    service._persist(source, candidates)
    db.commit()
    after = db.scalar(select(func.count(Victim.id)).where(Victim.group_id == group_id)) or 0
    return {"records_received": len(records), "created": max(after - before, 0), "total": after}
