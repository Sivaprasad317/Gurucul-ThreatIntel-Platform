from pydantic import BaseModel, Field, HttpUrl

class GroupCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$", max_length=100)
    parser_key: str = Field(min_length=2, max_length=100)
    actor_type: str = Field(default="Ransomware", max_length=80)
    description: str | None = None
    aliases: str | None = None
    first_observed_at: str | None = None
    discovery_date: str | None = None

class SourceCreate(BaseModel):
    """Request model for registering a crawl source."""

    group_id: str
    name: str = Field(min_length=2, max_length=200)
    base_url: str = Field(min_length=1, max_length=2000)
    source_page: str | None = None
    enabled: bool = True
