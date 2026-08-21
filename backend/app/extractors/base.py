from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class CandidateVictim:
    """Normalized output produced by one group-specific parser."""
    name: str
    source_page: str
    country: str | None = None
    industry: str | None = None
    description: str | None = None
    published_on: datetime | None = None
    discovered_on: datetime | None = None
    website: str | None = None


class GroupExtractor:
    parser_key = "base"

    def extract(self, html: str, source_page: str) -> list[CandidateVictim]:
        raise NotImplementedError
