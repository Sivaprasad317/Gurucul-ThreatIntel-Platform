from __future__ import annotations
from datetime import UTC, datetime
import re
from typing import Any
import httpx
from backend.app.core.config import get_settings


class RansomwareLiveClient:
    """Configurable adapter for Ransomware.live API Pro.

    The endpoint is intentionally supplied by configuration so a deployment
    uses the exact route documented for its API plan/version.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    def sync_payload(self, slug: str) -> list[dict[str, Any]]:
        endpoint = self.settings.ransomware_live_group_endpoint
        if not endpoint:
            raise RuntimeError(
                "Set RANSOMWARE_LIVE_GROUP_ENDPOINT to the exact group endpoint "
                "from your Ransomware.live API documentation."
            )
        url = endpoint.format(slug=slug)
        headers = {"Accept": "application/json", "User-Agent": "Gurucul-ThreatIntel-Platform/1.0"}
        if self.settings.ransomware_live_api_key:
            headers["Authorization"] = f"Bearer {self.settings.ransomware_live_api_key}"
            headers["X-API-Key"] = self.settings.ransomware_live_api_key
        with httpx.Client(timeout=self.settings.http_timeout_seconds, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            payload = response.json()
        return self._find_records(payload)

    @staticmethod
    def _find_records(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, dict)]
        if isinstance(payload, dict):
            for key in ("victims", "data", "results", "items", "records", "entries"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [x for x in value if isinstance(x, dict)]
            for value in payload.values():
                if isinstance(value, list) and all(isinstance(x, dict) for x in value):
                    return value
        raise ValueError("Could not find a victim record list in the API response.")

    @staticmethod
    def parse_date(value: Any) -> datetime | None:
        if not value:
            return None
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, UTC)
        if isinstance(value, str):
            raw = value.strip().replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(raw)
                return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
            except ValueError:
                for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
                    try:
                        return datetime.strptime(value.strip(), fmt).replace(tzinfo=UTC)
                    except ValueError:
                        pass
        return None

    @classmethod
    def normalize_record(cls, raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": raw.get("victim") or raw.get("name") or raw.get("company") or raw.get("organization"),
            "country": raw.get("country") or raw.get("country_code"),
            "industry": raw.get("industry") or raw.get("activity") or raw.get("sector"),
            "description": raw.get("description") or raw.get("summary"),
            "website": raw.get("website") or raw.get("domain"),
            "source_page": raw.get("post_url") or raw.get("source_page") or raw.get("url"),
            "published_on": cls.parse_date(raw.get("published") or raw.get("published_at") or raw.get("date")),
            "discovered_on": cls.parse_date(raw.get("discovered") or raw.get("discovered_at")),
        }
