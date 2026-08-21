from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from backend.app.extractors.base import CandidateVictim
from backend.app.services.normalization import (
    country_from_address,
    extract_domain,
    infer_country_from_domain,
    infer_industry,
)

logger = logging.getLogger(__name__)


class DragonForceExtractor:
    """Extract DragonForce victims from its guest blog API or Nuxt HTML."""

    parser_key = "dragonforce"

    API_PATH = "/api/guest/blog/posts"
    MAX_PAGES = 100

    def extract(
        self,
        html: str,
        source_page: str,
    ) -> list[CandidateVictim]:
        """Extract victims from a DragonForce Nuxt HTML page.

        This method is retained for local HTML/debug fixtures. Production
        crawling should normally use ``extract_api_pages`` because the
        DragonForce guest API exposes the complete paginated dataset.

        Parameters
        ----------
        html:
            Raw DragonForce HTML.
        source_page:
            Canonical DragonForce blog URL.

        Returns
        -------
        list[CandidateVictim]
            Extracted victims.

        Raises
        ------
        ValueError
            If the Nuxt JSON payload cannot be found or decoded.
        """
        soup = BeautifulSoup(html, "html.parser")

        scripts = soup.find_all(
            "script",
            attrs={"type": "application/json"},
        )

        if not scripts:
            raise ValueError(
                "DragonForce application/json payload was not found."
            )

        payload_script = max(
            scripts,
            key=lambda script: len(script.get_text()),
        )

        payload_text = payload_script.get_text().strip()

        if not payload_text:
            raise ValueError(
                "DragonForce application/json payload is empty."
            )

        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "DragonForce payload is not valid JSON."
            ) from exc

        if not isinstance(payload, list):
            raise ValueError(
                "DragonForce Nuxt payload root must be a list."
            )

        logger.info(
            "DragonForce Nuxt payload entries: %d",
            len(payload),
        )

        return self._extract_records(payload, source_page)

    def extract_api_pages(
        self,
        *,
        fetch_page: Any,
        source_page: str,
    ) -> tuple[list[CandidateVictim], int]:
        """Extract all victims from the DragonForce guest API.

        The observed API is:

            /api/guest/blog/posts?page=N

        Its response contains:

            {
                "data": {
                    "count": 610,
                    "publications": [...]
                }
            }

        Parameters
        ----------
        fetch_page:
            Callback supplied by CrawlService. It accepts ``url`` and
            ``page`` and returns a JSON dictionary.

        source_page:
            Configured DragonForce blog URL.

        Returns
        -------
        tuple[list[CandidateVictim], int]
            Deduplicated victims and number of API pages processed.

        Raises
        ------
        ValueError
            If the source URL or API response has an invalid shape.
        """
        api_url = self._get_api_url(source_page)

        all_candidates: list[CandidateVictim] = []
        seen: set[str] = set()

        total_count: int | None = None
        page = 1

        while page <= self.MAX_PAGES:
            payload = fetch_page(api_url, page)

            if not isinstance(payload, dict):
                raise ValueError(
                    f"DragonForce API page {page} returned "
                    "a non-object JSON response."
                )

            data = payload.get("data")

            if not isinstance(data, dict):
                raise ValueError(
                    f"DragonForce API page {page} is missing "
                    "the 'data' object."
                )

            if total_count is None:
                raw_count = data.get("count")
                try:
                    total_count = int(raw_count)
                except (TypeError, ValueError):
                    total_count = None

            publications = data.get("publications", [])

            if not isinstance(publications, list):
                raise ValueError(
                    f"DragonForce API page {page} has an invalid "
                    "'publications' value."
                )

            logger.info(
                "DragonForce API page=%d publications=%d total=%s",
                page,
                len(publications),
                total_count,
            )

            if not publications:
                break

            page_candidates = 0

            for publication in publications:
                if not isinstance(publication, dict):
                    continue

                candidate = self._build_candidate(
                    publication,
                    source_page,
                )

                if candidate is None:
                    continue

                identity = self._candidate_identity(
                    publication,
                    candidate,
                )

                if identity in seen:
                    continue

                seen.add(identity)
                all_candidates.append(candidate)
                page_candidates += 1

            # Stop when the API's declared total has been collected.
            if (
                total_count is not None
                and len(seen) >= total_count
            ):
                break

            # A short page is the natural end of pagination.
            if total_count is None and len(publications) == 0:
                break

            page += 1

        if page > self.MAX_PAGES:
            raise ValueError(
                f"DragonForce API pagination exceeded "
                f"{self.MAX_PAGES} pages."
            )

        logger.info(
            "DragonForce API extraction complete: "
            "pages=%d victims=%d declared_total=%s",
            page,
            len(all_candidates),
            total_count,
        )

        return all_candidates, page

    @classmethod
    def _get_api_url(cls, source_url: str) -> str:
        """Convert the configured blog URL to the guest API URL.

        Parameters
        ----------
        source_url:
            DragonForce blog URL.

        Returns
        -------
        str
            DragonForce guest API URL.

        Raises
        ------
        ValueError
            If the source URL is missing or invalid.
        """
        if not isinstance(source_url, str):
            raise ValueError(
                f"Invalid DragonForce source URL: {source_url!r}"
            )

        value = source_url.strip()

        if value.casefold() in {
            "",
            "null",
            "none",
            "undefined",
            "nil",
        }:
            raise ValueError(
                f"Invalid DragonForce source URL: {source_url!r}"
            )

        parsed = urlparse(value)

        if parsed.scheme not in {"http", "https"}:
            raise ValueError(
                f"Invalid DragonForce source URL: {value!r}"
            )

        if not parsed.netloc:
            raise ValueError(
                f"Invalid DragonForce source URL: {value!r}"
            )

        return f"{parsed.scheme}://{parsed.netloc}{cls.API_PATH}"

    def _extract_records(
        self,
        payload: list[Any],
        source_page: str,
    ) -> list[CandidateVictim]:
        """Find victim dictionaries inside a Nuxt payload."""
        result: list[CandidateVictim] = []
        seen: set[str] = set()

        for index, value in enumerate(payload):
            if not isinstance(value, dict):
                continue

            if not self._looks_like_victim(value):
                continue

            record = self._resolve_record(value, payload)

            if not record:
                continue

            candidate = self._build_candidate(
                record,
                source_page,
            )

            if candidate is None:
                continue

            key = candidate.name.casefold()

            if key in seen:
                continue

            seen.add(key)
            result.append(candidate)

            logger.debug(
                "DragonForce victim %d: %s",
                index,
                candidate.name,
            )

        return result

    def _resolve_record(
        self,
        value: dict[str, Any],
        payload: list[Any],
    ) -> dict[str, Any] | None:
        """Resolve only the fields belonging to one Nuxt victim."""
        result: dict[str, Any] = {}

        fields = (
            "uuid",
            "created_at",
            "name",
            "website",
            "address",
            "description",
        )

        for field in fields:
            if field not in value:
                continue

            result[field] = self._resolve_reference(
                value[field],
                payload,
            )

        if not self._looks_like_victim(result):
            return None

        return result

    @classmethod
    def _resolve_reference(
        cls,
        value: Any,
        payload: list[Any],
        *,
        _depth: int = 0,
    ) -> Any:
        """Safely resolve Nuxt integer references.

        Handles nested integer/list references without assuming that
        every list value is an integer reference. A depth limit prevents
        malformed payloads from causing infinite recursion.
        """
        if _depth > 20:
            return None

        if isinstance(value, bool):
            return value

        if not isinstance(value, int):
            return value

        if value < 0 or value >= len(payload):
            return None

        resolved = payload[value]

        if isinstance(resolved, str):
            return resolved

        if (
            isinstance(resolved, list)
            and len(resolved) == 2
            and isinstance(resolved[1], int)
        ):
            return cls._resolve_reference(
                resolved[1],
                payload,
                _depth=_depth + 1,
            )

        return resolved

    def _build_candidate(
        self,
        value: dict[str, Any],
        source_page: str,
    ) -> CandidateVictim | None:
        """Convert one DragonForce publication into CandidateVictim."""
        name = self._clean(value.get("name"))

        if not name:
            return None

        website = self._clean(value.get("website"))
        address = self._clean(value.get("address"))
        description = self._clean(value.get("description"))

        published_on = self._parse_datetime(
            value.get("created_at")
        )

        # Prefer explicit address evidence.
        country = country_from_address(address)

        # Fall back to a country-code domain only when the address
        # does not provide a country.
        if country is None:
            domain = extract_domain(website)

            country_code, _, _ = infer_country_from_domain(
                domain
            )

            country = country_code

        industry_text = " ".join(
            part
            for part in (
                name,
                description,
                address,
            )
            if part
        )

        _, industry_name, _ = infer_industry(
            industry_text
        )

        return CandidateVictim(
            name=name,
            source_page=source_page,
            country=country,
            industry=industry_name,
            website=website,
            description=self._build_description(
                description=description,
                website=website,
                address=address,
            ),
            published_on=published_on,
            discovered_on=published_on,
        )

    @staticmethod
    def _candidate_identity(
        publication: dict[str, Any],
        candidate: CandidateVictim,
    ) -> str:
        """Return a stable identity for API deduplication."""
        uuid = publication.get("uuid")

        if isinstance(uuid, str) and uuid.strip():
            return f"uuid:{uuid.strip().casefold()}"

        return f"name:{candidate.name.casefold()}"

    @staticmethod
    def _looks_like_victim(
        value: dict[str, Any],
    ) -> bool:
        """Check whether a dictionary resembles a victim record."""
        required_fields = {
            "uuid",
            "created_at",
            "name",
            "website",
            "address",
            "description",
        }

        return required_fields.issubset(value)

    @staticmethod
    def _clean(value: Any) -> str | None:
        """Normalize a value into a string."""
        if value is None or not isinstance(value, str):
            return None

        text = value.strip()

        return text or None

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        """Parse a DragonForce ISO timestamp."""
        if not isinstance(value, str):
            return None

        text = value.strip()

        if not text:
            return None

        try:
            result = datetime.fromisoformat(
                text.replace("Z", "+00:00")
            )
        except ValueError:
            logger.warning(
                "Unable to parse DragonForce timestamp: %r",
                value,
            )
            return None

        if result.tzinfo is None:
            result = result.replace(tzinfo=UTC)

        return result

    @staticmethod
    def _build_description(
        *,
        description: str | None,
        website: str | None,
        address: str | None,
    ) -> str | None:
        """Build a useful victim description."""
        parts: list[str] = []

        if description:
            parts.append(description)

        if website:
            parts.append(f"Website: {website}")

        if address:
            parts.append(f"Address: {address}")

        return "\n".join(parts) or None


EXTRACTOR = DragonForceExtractor()
