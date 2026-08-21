from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ActorCard(BaseModel):
    id: str
    name: str
    slug: str
    status: str
    actor_type: str
    victims: int

class DashboardOverview(BaseModel):
    actor: dict
    kpis: dict
    quality: dict
    health: dict

class VictimRead(BaseModel):
    id: str
    name: str
    country_code: str | None
    country_name: str | None
    industry_code: str | None
    industry_name: str | None
    description: str | None
    published_on: datetime | None
    discovered_on: datetime | None
    source_page: str
    first_seen_at: datetime
    last_seen_at: datetime

class CrawlRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    group_id: str
    status: str
    pages_discovered: int
    victims_found: int
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
