from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.routes import router
from backend.app.core.config import get_settings
from backend.app.db.base import Base
from backend.app.db.session import SessionLocal, engine
from backend.app.models import CrawlJob, VictimEnrichment, ThreatGroup, Source, User, Victim
from backend.app.services.bootstrap import ensure_admin

@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        ensure_admin(session)
    yield

settings = get_settings()
app = FastAPI(
    title="Gurucul ThreatIntel Platform",
    version="1.0.0",
    description="Actor-scoped ransomware threat intelligence and collection analytics.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in settings.cors_origins.split(",") if x.strip()],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
app.include_router(router)

@app.get("/")
def root() -> dict:
    return {"name": "Gurucul ThreatIntel Platform", "status": "ok", "demo_mode": settings.demo_mode}
