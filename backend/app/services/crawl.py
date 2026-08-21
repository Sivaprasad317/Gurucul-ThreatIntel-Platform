from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlparse
from uuid import UUID

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.extractors.registry import get_extractor
from backend.app.extractors.base import CandidateVictim
from backend.app.models.crawl import CrawlJob
from backend.app.models.group import ThreatGroup
from backend.app.models.source import Source
from backend.app.models.victim import Victim
from backend.app.services.normalization import (
    COUNTRIES,
    INDUSTRIES,
    country_from_value,
    extract_domain,
    infer_industry,
)

logger = logging.getLogger(__name__)


class CrawlSourceNotFoundError(LookupError):
    """Raised when a configured source does not exist."""


class CrawlExecutionError(RuntimeError):
    """Raised when a crawl fails."""


class CrawlJobNotFoundError(LookupError):
    """Raised when a crawl job does not exist."""


class CrawlService:
    """Run configured threat-intelligence sources."""

    MAX_PAGES = 100
    FETCH_RETRIES = 3
    RETRY_BACKOFF_SECONDS = 2.0
    USER_AGENT = "Gurucul-ThreatIntel-Platform/1.0"

    def __init__(self, session: Session) -> None:
        """Initialize the crawl service.

        Parameters
        ----------
        session:
            SQLAlchemy database session.
        """
        self.session = session
        self.settings = get_settings()

    def _get_source_url(self, source: Source) -> str:
        """Return a valid configured source URL."""
        candidates = (
            getattr(source, "source_page", None),
            getattr(source, "base_url", None),
        )

        for candidate in candidates:
            if not isinstance(candidate, str):
                continue

            value = candidate.strip()

            if value.casefold() in {
                "",
                "null",
                "none",
                "undefined",
                "nil",
            }:
                continue

            parsed = urlparse(value)

            if parsed.scheme not in {"http", "https"}:
                continue

            if not parsed.netloc:
                continue

            return value

        raise CrawlExecutionError(
            f"Source '{source.id}' has no valid configured URL."
        )

    def get(self, job_id: UUID) -> CrawlJob:
        """Return a crawl job by ID."""
        job = self.session.scalar(
            select(CrawlJob).where(CrawlJob.id == job_id)
        )

        if job is None:
            raise CrawlJobNotFoundError(
                f"Crawl job '{job_id}' was not found."
            )

        return job

    def crawl(self, source_id: UUID) -> CrawlJob:
        """Backward-compatible crawl entry point."""
        return self.crawl_source(source_id)

    def crawl_source(self, source_id: UUID) -> CrawlJob:
        """Crawl one configured source."""
        source = self.session.scalar(
            select(Source).where(Source.id == source_id)
        )

        if source is None:
            raise CrawlSourceNotFoundError(
                f"Source '{source_id}' was not found."
            )

        if getattr(source, "enabled", True) is False:
            raise CrawlExecutionError(
                f"Source '{source_id}' is disabled."
            )

        group = self.session.scalar(
            select(ThreatGroup).where(
                ThreatGroup.id == source.group_id
            )
        )

        if group is None:
            raise CrawlExecutionError(
                f"Threat group '{source.group_id}' was not found."
            )

        parser_key = group.parser_key

        if not parser_key:
            raise CrawlExecutionError(
                f"Threat group '{group.id}' does not have a parser_key."
            )

        try:
            extractor = get_extractor(parser_key)
        except Exception as exc:
            logger.exception(
                "Unable to load extractor: parser=%s source=%s",
                parser_key,
                source_id,
            )
            raise CrawlExecutionError(
                f"Unable to load extractor '{parser_key}': {exc}"
            ) from exc

        now = datetime.now(UTC)

        job = CrawlJob(
            source_id=source.id,
            group_id=source.group_id,
            status="running",
            pages_discovered=0,
            victims_found=0,
            started_at=now,
            finished_at=None,
            error_message=None,
        )

        self.session.add(job)

        try:
            self.session.flush()
        except Exception as exc:
            self.session.rollback()
            raise CrawlExecutionError(
                f"Unable to create crawl job: {exc}"
            ) from exc

        try:
            source_page = self._get_source_url(source)

            logger.info(
                "Starting crawl: source=%s group=%s parser=%s url=%s",
                source.id,
                group.id,
                parser_key,
                source_page,
            )

            extract_api_pages = getattr(
                extractor,
                "extract_api_pages",
                None,
            )

            if callable(extract_api_pages):
                candidates, pages_discovered = self._crawl_api_pages(
                    extract_api_pages=extract_api_pages,
                    source_page=source_page,
                )
            else:
                candidates, pages_discovered = self._crawl_html_pages(
                    extractor=extractor,
                    source_url=source.base_url,
                    source_page=source_page,
                )

            logger.info(
                "Extraction complete: source=%s pages=%d candidates=%d",
                source.id,
                pages_discovered,
                len(candidates),
            )

            persisted_count = self._persist_candidates(
                source,
                candidates,
            )

            job.pages_discovered = pages_discovered
            job.victims_found = persisted_count
            job.status = "completed"
            job.finished_at = datetime.now(UTC)
            job.error_message = None

            if hasattr(source, "last_status"):
                source.last_status = "completed"

            if hasattr(source, "last_crawled_at"):
                source.last_crawled_at = datetime.now(UTC)

            self.session.commit()

            logger.info(
                "Crawl completed: source=%s job=%s pages=%d victims=%d",
                source.id,
                job.id,
                pages_discovered,
                persisted_count,
            )

            return job

        except Exception as exc:
            self.session.rollback()

            error_message = str(exc)[:4000]

            logger.exception(
                "Crawl failed: source=%s",
                source_id,
            )

            try:
                failed_job = CrawlJob(
                    source_id=source.id,
                    group_id=source.group_id,
                    status="failed",
                    pages_discovered=0,
                    victims_found=0,
                    started_at=now,
                    finished_at=datetime.now(UTC),
                    error_message=error_message,
                )

                self.session.add(failed_job)
                self.session.commit()
            except Exception:
                self.session.rollback()
                logger.exception(
                    "Unable to persist failed crawl job: source=%s",
                    source_id,
                )

            if isinstance(exc, CrawlExecutionError):
                raise

            raise CrawlExecutionError(
                f"Crawl failed for source '{source_id}': {exc}"
            ) from exc

    def _crawl_api_pages(
        self,
        *,
        extract_api_pages: Callable[..., Any],
        source_page: str,
    ) -> tuple[list[CandidateVictim], int]:
        """Run extractor-owned API pagination."""
        try:
            result = extract_api_pages(
                fetch_page=self._fetch_json,
                source_page=source_page,
            )
        except CrawlExecutionError:
            raise
        except Exception as exc:
            raise CrawlExecutionError(
                f"Extractor API pagination failed: {exc}"
            ) from exc

        if not isinstance(result, tuple) or len(result) != 2:
            raise CrawlExecutionError(
                "extract_api_pages() must return "
                "(candidates, pages_discovered)."
            )

        candidates, pages = result

        if not isinstance(candidates, list):
            raise CrawlExecutionError(
                "Extractor API pagination did not return a candidate list."
            )

        try:
            page_count = int(pages)
        except (TypeError, ValueError) as exc:
            raise CrawlExecutionError(
                "Extractor API pagination returned an invalid page count."
            ) from exc

        return candidates, max(page_count, 0)

    def _crawl_html_pages(
        self,
        *,
        extractor: Any,
        source_url: str,
        source_page: str,
    ) -> tuple[list[CandidateVictim], int]:
        """Crawl a source using HTML pagination."""
        candidates: list[CandidateVictim] = []
        current_url: str | None = source_url
        visited_urls: set[str] = set()
        pages_processed = 0

        while current_url:
            normalized_url = self._normalize_url(current_url)

            if normalized_url in visited_urls:
                logger.warning(
                    "Pagination loop detected: %s",
                    current_url,
                )
                break

            if pages_processed >= self.MAX_PAGES:
                raise CrawlExecutionError(
                    f"HTML pagination exceeded {self.MAX_PAGES} pages."
                )

            visited_urls.add(normalized_url)

            logger.info(
                "Fetching HTML page %d/%d: %s",
                pages_processed + 1,
                self.MAX_PAGES,
                current_url,
            )

            html = self._fetch(current_url)
            pages_processed += 1

            try:
                page_candidates = extractor.extract(
                    html,
                    source_page,
                )
            except Exception as exc:
                raise CrawlExecutionError(
                    f"Extractor failed on page '{current_url}': {exc}"
                ) from exc

            if not isinstance(page_candidates, list):
                raise CrawlExecutionError(
                    "Extractor.extract() must return a list."
                )

            candidates.extend(page_candidates)

            next_url = self._find_next_page_url(
                html,
                current_url,
            )

            if next_url is None:
                break

            current_url = next_url

        return candidates, pages_processed

    def _build_timeout(self) -> httpx.Timeout:
        """Build HTTP timeout configuration."""
        timeout_seconds = float(
            getattr(
                self.settings,
                "http_timeout_seconds",
                60,
            )
        )

        timeout_seconds = max(timeout_seconds, 10.0)

        return httpx.Timeout(
            timeout=timeout_seconds,
            connect=max(timeout_seconds, 60.0),
            read=max(timeout_seconds, 60.0),
            write=max(timeout_seconds, 60.0),
            pool=max(timeout_seconds, 60.0),
        )

    def _create_http_client(self) -> httpx.Client:
        """Create a configured HTTP client."""
        kwargs: dict[str, Any] = {
            "timeout": self._build_timeout(),
            "follow_redirects": True,
            "headers": {
                "User-Agent": self.USER_AGENT,
            },
        }

        tor_proxy = getattr(
            self.settings,
            "tor_proxy",
            None,
        )

        if tor_proxy:
            kwargs["proxy"] = tor_proxy

        return httpx.Client(**kwargs)

    def _fetch(self, url: str) -> str:
        """Fetch HTML from a URL."""
        with self._create_http_client() as client:
            return self._fetch_with_client(client, url)

    def _fetch_with_client(
        self,
        client: httpx.Client,
        url: str,
    ) -> str:
        """Fetch HTML with retries."""
        last_error: Exception | None = None

        for attempt in range(1, self.FETCH_RETRIES + 1):
            try:
                response = client.get(url)
                response.raise_for_status()
                return response.text

            except (
                httpx.TimeoutException,
                httpx.NetworkError,
                httpx.RemoteProtocolError,
                httpx.HTTPStatusError,
            ) as exc:
                last_error = exc

                if (
                    isinstance(exc, httpx.HTTPStatusError)
                    and exc.response.status_code < 500
                ):
                    raise CrawlExecutionError(
                        f"HTTP {exc.response.status_code} while fetching '{url}'."
                    ) from exc

                if attempt < self.FETCH_RETRIES:
                    delay = self.RETRY_BACKOFF_SECONDS * (
                        2 ** (attempt - 1)
                    )
                    logger.warning(
                        "Fetch failed: attempt=%d/%d url=%s error=%s retry_in=%.1fs",
                        attempt,
                        self.FETCH_RETRIES,
                        url,
                        exc,
                        delay,
                    )
                    time.sleep(delay)

        raise CrawlExecutionError(
            f"Unable to fetch '{url}' after "
            f"{self.FETCH_RETRIES} attempts: {last_error}"
        ) from last_error

    def _fetch_json(
        self,
        url: str,
        page: int,
    ) -> dict[str, Any]:
        """Fetch one paginated JSON API response."""
        last_error: Exception | None = None

        for attempt in range(1, self.FETCH_RETRIES + 1):
            try:
                kwargs: dict[str, Any] = {
                    "timeout": self._build_timeout(),
                    "follow_redirects": True,
                    "headers": {
                        "User-Agent": self.USER_AGENT,
                        "Accept": "application/json",
                    },
                }

                tor_proxy = getattr(
                    self.settings,
                    "tor_proxy",
                    None,
                )

                if tor_proxy:
                    kwargs["proxy"] = tor_proxy

                with httpx.Client(**kwargs) as client:
                    response = client.get(
                        url,
                        params={"page": page},
                    )
                    response.raise_for_status()

                    payload = response.json()

                    if not isinstance(payload, dict):
                        raise ValueError(
                            "Expected API response to be a JSON object."
                        )

                    logger.info(
                        "Fetched API page %d: status=%d bytes=%d",
                        page,
                        response.status_code,
                        len(response.content),
                    )

                    return payload

            except (
                httpx.TimeoutException,
                httpx.NetworkError,
                httpx.RemoteProtocolError,
                httpx.HTTPStatusError,
                ValueError,
            ) as exc:
                last_error = exc

                if (
                    isinstance(exc, httpx.HTTPStatusError)
                    and exc.response.status_code < 500
                ):
                    raise CrawlExecutionError(
                        f"API page {page} returned HTTP "
                        f"{exc.response.status_code}."
                    ) from exc

                if attempt < self.FETCH_RETRIES:
                    delay = self.RETRY_BACKOFF_SECONDS * (
                        2 ** (attempt - 1)
                    )
                    logger.warning(
                        "API fetch failed: page=%d attempt=%d/%d "
                        "error=%s retry_in=%.1fs",
                        page,
                        attempt,
                        self.FETCH_RETRIES,
                        exc,
                        delay,
                    )
                    time.sleep(delay)

        raise CrawlExecutionError(
            f"Unable to fetch API page {page} after "
            f"{self.FETCH_RETRIES} attempts: {last_error}"
        ) from last_error

    @staticmethod
    def _find_next_page_url(
        html: str,
        current_url: str,
    ) -> str | None:
        """Find the next page URL in HTML."""
        soup = BeautifulSoup(html, "html.parser")

        link = soup.select_one('a[rel~="next"][href]')

        if link is not None:
            href = link.get("href")
            if isinstance(href, str) and href.strip():
                return urljoin(current_url, href.strip())

        selectors = (
            "ul.pagination li.next:not(.disabled) a[href]",
            "a.next[href]",
            "li.next:not(.disabled) a[href]",
            ".pagination .next:not(.disabled) a[href]",
        )

        for selector in selectors:
            link = soup.select_one(selector)

            if link is None:
                continue

            href = link.get("href")

            if isinstance(href, str) and href.strip():
                return urljoin(current_url, href.strip())

        return None

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalize URL for pagination detection."""
        return url.rstrip("/")

    # ==================================================================
    # DATABASE PERSISTENCE
    # ==================================================================

    def _persist_candidates(
        self,
        source: Source,
        candidates: list[CandidateVictim],
    ) -> int:
        """Persist candidates using the ACTUAL Victim model fields.

        The Victim model in this project has:
            country_code / country_name
            industry_code / industry_name

        It does NOT have:
            country
            industry
        """
        created = 0
        updated = 0
        skipped = 0
        now = datetime.now(UTC)

        existing_victims = self.session.scalars(
            select(Victim).where(
                Victim.source_id == source.id
            )
        ).all()

        existing_by_name: dict[str, Victim] = {}

        for victim in existing_victims:
            normalized_name = self._normalize_victim_name(
                victim.name
            )

            if normalized_name:
                existing_by_name[normalized_name] = victim

        for candidate in candidates:
            normalized_name = self._normalize_victim_name(
                candidate.name
            )

            if not normalized_name:
                skipped += 1
                continue

            name = " ".join(candidate.name.split()).strip()

            country_code, country_name, country_confidence = (
                country_from_value(
                    getattr(candidate, "country", None)
                )
            )

            industry_code, industry_name, industry_confidence = (
                self._resolve_industry(
                    getattr(candidate, "industry", None)
                )
            )

            website = getattr(candidate, "website", None)
            domain = extract_domain(website)

            victim = existing_by_name.get(
                normalized_name
            )

            if victim is None:
                victim = Victim(
                    source_id=source.id,
                    group_id=source.group_id,
                    name=name,
                    normalized_name=normalized_name,
                    domain=domain,
                    country_code=country_code,
                    country_name=country_name,
                    industry_code=industry_code,
                    industry_name=industry_name,
                    country_source=(
                        "source" if country_code else None
                    ),
                    industry_source=(
                        "source" if industry_code else None
                    ),
                    country_confidence=country_confidence,
                    industry_confidence=industry_confidence,
                    country_evidence=(
                        candidate.source_page
                        if country_code
                        else None
                    ),
                    industry_evidence=(
                        candidate.source_page
                        if industry_code
                        else None
                    ),
                    description=getattr(
                        candidate,
                        "description",
                        None,
                    ),
                    published_on=getattr(
                        candidate,
                        "published_on",
                        None,
                    ),
                    discovered_on=getattr(
                        candidate,
                        "discovered_on",
                        None,
                    ),
                    source_page=getattr(
                        candidate,
                        "source_page",
                        None,
                    ),
                    first_seen_at=now,
                    last_seen_at=now,
                )

                self.session.add(victim)
                existing_by_name[normalized_name] = victim
                created += 1
                continue

            changed = False

            # Never replace good database values with None.
            if name and victim.name != name:
                victim.name = name
                changed = True

            if domain and victim.domain != domain:
                victim.domain = domain
                changed = True

            if country_code and victim.country_code != country_code:
                victim.country_code = country_code
                changed = True

            if country_name and victim.country_name != country_name:
                victim.country_name = country_name
                changed = True

            if industry_code and victim.industry_code != industry_code:
                victim.industry_code = industry_code
                changed = True

            if industry_name and victim.industry_name != industry_name:
                victim.industry_name = industry_name
                changed = True

            description = getattr(
                candidate,
                "description",
                None,
            )

            if description and victim.description != description:
                victim.description = description
                changed = True

            published_on = getattr(
                candidate,
                "published_on",
                None,
            )

            if published_on and victim.published_on != published_on:
                victim.published_on = published_on
                changed = True

            discovered_on = getattr(
                candidate,
                "discovered_on",
                None,
            )

            if discovered_on and victim.discovered_on != discovered_on:
                victim.discovered_on = discovered_on
                changed = True

            source_page = getattr(
                candidate,
                "source_page",
                None,
            )

            if source_page and victim.source_page != source_page:
                victim.source_page = source_page
                changed = True

            if victim.last_seen_at != now:
                victim.last_seen_at = now
                changed = True

            if changed:
                updated += 1

        logger.info(
            "Victim persistence complete: "
            "source=%s created=%d updated=%d skipped=%d",
            source.id,
            created,
            updated,
            skipped,
        )

        return created + updated

    @staticmethod
    def _resolve_industry(
        value: str | None,
    ) -> tuple[str | None, str | None, float | None]:
        """Resolve a candidate industry into code, label and confidence."""
        if not value:
            return None, None, None

        raw = value.strip()

        if not raw:
            return None, None, None

        # CandidateVictim normally contains the human-readable label,
        # e.g. "Manufacturing" or "Aerospace & Defense".
        for code, label in INDUSTRIES:
            if raw.casefold() == label.casefold():
                return code, label, 1.0

        # Also accept an industry code.
        for code, label in INDUSTRIES:
            if raw.casefold() == code.casefold():
                return code, label, 1.0

        # Finally allow the existing keyword inference logic.
        return infer_industry(raw)

    @staticmethod
    def _normalize_victim_name(
        name: str | None,
    ) -> str:
        """Normalize victim name for deduplication."""
        if not name:
            return ""

        return " ".join(name.split()).casefold()
