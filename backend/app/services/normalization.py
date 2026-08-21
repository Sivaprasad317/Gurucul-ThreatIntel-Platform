from __future__ import annotations

import re
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# Countries
# ---------------------------------------------------------------------------

COUNTRIES: dict[str, str] = {
    "US": "United States",
    "GB": "United Kingdom",
    "DE": "Germany",
    "CA": "Canada",
    "FR": "France",
    "IT": "Italy",
    "AU": "Australia",
    "IN": "India",
    "CN": "China",
    "HK": "Hong Kong",
    "JP": "Japan",
    "BR": "Brazil",
    "ES": "Spain",
    "NL": "Netherlands",
    "BE": "Belgium",
    "SE": "Sweden",
    "NO": "Norway",
    "DK": "Denmark",
    "FI": "Finland",
    "CH": "Switzerland",
    "AT": "Austria",
    "IE": "Ireland",
    "PL": "Poland",
    "PT": "Portugal",
    "MX": "Mexico",
    "SG": "Singapore",
    "NZ": "New Zealand",
    "ZA": "South Africa",
    "AE": "United Arab Emirates",
    "IL": "Israel",
    "KR": "South Korea",
    "TW": "Taiwan",
    "TR": "Turkey",
    "CZ": "Czechia",
    "RO": "Romania",
    "HU": "Hungary",
    "GR": "Greece",
    "UA": "Ukraine",
    "RU": "Russia",
    "SA": "Saudi Arabia",
    "HT": "Haiti",
}


# ---------------------------------------------------------------------------
# Country aliases
# ---------------------------------------------------------------------------

COUNTRY_ALIASES: dict[str, str] = {
    "usa": "US",
    "u.s.a.": "US",
    "u.s.a": "US",
    "u.s.": "US",
    "u.s": "US",
    "united states of america": "US",

    "uk": "GB",
    "u.k.": "GB",
    "u.k": "GB",
    "england": "GB",
    "scotland": "GB",
    "wales": "GB",
    "northern ireland": "GB",

    "south korea": "KR",
    "republic of korea": "KR",
    "korea": "KR",

    "czech republic": "CZ",

    "russia": "RU",
    "russian federation": "RU",

    "turkiye": "TR",
    "türkiye": "TR",

    "saudi arabia": "SA",

    "haiti": "HT",
    "port-au-prince": "HT",
    "port au prince": "HT",
}


# ---------------------------------------------------------------------------
# US states
#
# IMPORTANT:
# We deliberately do NOT use two-letter postal abbreviations such as:
#
#     WV
#     CA
#     TX
#     FL
#
# because they can occur naturally inside ordinary text/domain names.
#
# Full state names are safer.
# ---------------------------------------------------------------------------

US_STATES: tuple[str, ...] = (
    "Alabama",
    "Alaska",
    "Arizona",
    "Arkansas",
    "California",
    "Colorado",
    "Connecticut",
    "Delaware",
    "Florida",
    "Georgia",
    "Hawaii",
    "Idaho",
    "Illinois",
    "Indiana",
    "Iowa",
    "Kansas",
    "Kentucky",
    "Louisiana",
    "Maine",
    "Maryland",
    "Massachusetts",
    "Michigan",
    "Minnesota",
    "Mississippi",
    "Missouri",
    "Montana",
    "Nebraska",
    "Nevada",
    "New Hampshire",
    "New Jersey",
    "New Mexico",
    "New York",
    "North Carolina",
    "North Dakota",
    "Ohio",
    "Oklahoma",
    "Oregon",
    "Pennsylvania",
    "Rhode Island",
    "South Carolina",
    "South Dakota",
    "Tennessee",
    "Texas",
    "Utah",
    "Vermont",
    "Virginia",
    "Washington",
    "West Virginia",
    "Wisconsin",
    "Wyoming",
)


# ---------------------------------------------------------------------------
# Industry taxonomy
# ---------------------------------------------------------------------------

INDUSTRIES: list[tuple[str, str]] = [
    ("manufacturing", "Manufacturing"),
    ("professional-services", "Professional Services"),
    ("technology", "Technology"),
    ("healthcare", "Healthcare"),
    ("financial-services", "Financial Services"),
    ("retail", "Retail & E-Commerce"),
    ("transportation", "Transportation & Logistics"),
    ("construction", "Construction"),
    ("energy", "Energy & Utilities"),
    ("telecommunications", "Telecommunications"),
    ("education", "Education"),
    ("government", "Government & Public Sector"),
    ("agriculture", "Agriculture & Food"),
    ("hospitality", "Hospitality & Tourism"),
    ("media", "Media & Entertainment"),
    ("real-estate", "Real Estate"),
    ("automotive", "Automotive"),
    ("aerospace", "Aerospace & Defense"),
    ("pharma", "Pharmaceuticals & Biotechnology"),
    ("nonprofit", "Nonprofit"),
    ("other", "Other"),
]


INDUSTRY_KEYWORDS: dict[str, list[str]] = {
    "manufacturing": [
        "manufacturing",
        "manufacturer",
        "industrial",
        "factory",
        "machining",
        "machined",
        "fabrication",
        "production",
    ],
    "professional-services": [
        "consulting",
        "consultancy",
        "law firm",
        "legal",
        "accounting",
        "accountancy",
        "advisory",
        "chartered accountant",
        "business advisory",
    ],
    "technology": [
        "software",
        "technology",
        "saas",
        "cloud",
        "cybersecurity",
        "cyber security",
        "it services",
        "information technology",
        "programming",
        "contact center",
        "contact centre",
        "service desk",
        "help desk",
    ],
    "healthcare": [
        "hospital",
        "healthcare",
        "medical",
        "clinic",
        "pharma",
        "health",
        "eyecare",
        "eye care",
        "surgery",
        "patient",
        "dental",
    ],
    "financial-services": [
        "bank",
        "banking",
        "insurance",
        "financial",
        "credit union",
        "investment",
        "mortgage",
        "accounting",
        "wealth management",
        "finance",
    ],
    "retail": [
        "retail",
        "store",
        "e-commerce",
        "ecommerce",
        "shop",
        "beauty products",
        "consumer products",
        "personal care",
    ],
    "transportation": [
        "logistics",
        "transport",
        "shipping",
        "freight",
        "airline",
        "airport",
        "trucking",
        "delivery",
        "courier",
    ],
    "construction": [
        "construction",
        "contractor",
        "building",
        "builder",
        "civil engineering",
        "hvac",
        "heating and air conditioning",
        "plumbing",
        "roofing",
    ],
    "energy": [
        "energy",
        "utility",
        "utilities",
        "oil",
        "gas",
        "electric",
        "power generation",
        "petroleum",
    ],
    "telecommunications": [
        "telecom",
        "telecommunications",
        "wireless",
        "communications",
        "mobile network",
        "internet service provider",
    ],
    "education": [
        "university",
        "college",
        "school",
        "education",
        "academy",
        "educational",
    ],
    "government": [
        "government",
        "municipality",
        "ministry",
        "county",
        "city of",
        "public sector",
        "municipal",
        "government agency",
    ],
    "agriculture": [
        "agriculture",
        "farming",
        "farm",
        "food production",
        "food processing",
        "agricultural",
    ],
    "hospitality": [
        "hotel",
        "hospitality",
        "tourism",
        "resort",
        "travel",
        "leisure",
        "holiday",
    ],
    "media": [
        "media",
        "publishing",
        "publisher",
        "broadcast",
        "entertainment",
        "news",
    ],
    "real-estate": [
        "real estate",
        "property",
        "properties",
        "realtor",
        "estate agency",
        "property management",
    ],
    "automotive": [
        "automotive",
        "vehicle",
        "motor",
        "car dealer",
        "dealership",
        "automobile",
    ],
    "aerospace": [
        "aerospace",
        "defense",
        "defence",
        "aircraft",
        "space industry",
        "spacecraft",
    ],
    "pharma": [
        "pharmaceutical",
        "biotech",
        "biotechnology",
        "drug development",
        "life sciences",
    ],
    "nonprofit": [
        "nonprofit",
        "non-profit",
        "foundation",
        "charity",
        "charitable",
    ],
}


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def normalize_name(name: str) -> str:
    """Normalize a victim name for comparison and deduplication.

    Parameters
    ----------
    name:
        Raw victim name.

    Returns
    -------
    str
        Whitespace-normalized, case-folded name.
    """
    return " ".join(name.split()).casefold()


def country_from_address(
    address: str | None,
) -> str | None:
    """Infer a country from a source-provided postal/location address.

    Parameters
    ----------
    address:
        Free-form postal address.

    Returns
    -------
    str | None
        ISO-3166 alpha-2 country code when detected.

    Notes
    -----
    This function intentionally does not inspect company names or
    descriptions.

    It also does not use two-letter US postal abbreviations because
    values such as ``CA`` or ``IN`` can occur naturally in ordinary
    text and produce false positives.

    Bare domain names are not treated as US state locations. For
    example, ``vermont.com.br`` must not become ``US`` merely because
    ``Vermont`` is a US state.
    """
    if not address:
        return None

    text = " ".join(
        str(address).strip().split()
    )

    if not text:
        return None

    normalized = text.casefold()

    # ---------------------------------------------------------------
    # Domain detection
    # ---------------------------------------------------------------
    #
    # If the value is clearly a domain name, do not interpret a word
    # in the domain as a US state.
    #
    # Example:
    #
    #     vermont.com.br
    #
    # must NOT become:
    #
    #     Vermont -> US
    #
    if _looks_like_domain(normalized):
        return None

    # ---------------------------------------------------------------
    # Explicit country names
    # ---------------------------------------------------------------

    for code, country_name in sorted(
        COUNTRIES.items(),
        key=lambda item: len(item[1]),
        reverse=True,
    ):
        if _contains_phrase(
            normalized,
            country_name,
        ):
            return code

    # ---------------------------------------------------------------
    # Country aliases / cities
    # ---------------------------------------------------------------

    for alias, code in sorted(
        COUNTRY_ALIASES.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        if _contains_phrase(
            normalized,
            alias,
        ):
            return code

    # ---------------------------------------------------------------
    # US full state names
    # ---------------------------------------------------------------
    #
    # Only full names are considered.
    #
    # We do not use:
    #
    #     CA
    #     TX
    #     WV
    #     FL
    #
    # because those can produce false positives.
    # ---------------------------------------------------------------

    for state in sorted(
        US_STATES,
        key=len,
        reverse=True,
    ):
        if _contains_phrase(
            normalized,
            state,
        ):
            return "US"

    return None


def country_from_value(
    value: str | None,
) -> tuple[str | None, str | None, float | None]:
    """Resolve an explicit country value.

    Parameters
    ----------
    value:
        Country code or country name.

    Returns
    -------
    tuple[str | None, str | None, float | None]
        Country code, country name, and confidence.
    """
    if not value:
        return None, None, None

    raw = " ".join(
        value.strip().split()
    )

    if not raw:
        return None, None, None

    upper = raw.upper()

    if upper in COUNTRIES:
        return (
            upper,
            COUNTRIES[upper],
            1.0,
        )

    for code, label in COUNTRIES.items():
        if raw.casefold() == label.casefold():
            return (
                code,
                label,
                1.0,
            )

    for alias, code in COUNTRY_ALIASES.items():
        if raw.casefold() == alias.casefold():
            return (
                code,
                COUNTRIES[code],
                0.95,
            )

    return None, None, None


def infer_country_from_domain(
    domain: str | None,
) -> tuple[str | None, str | None, float | None]:
    """Infer country from a website country-code top-level domain.

    Parameters
    ----------
    domain:
        Website hostname.

    Returns
    -------
    tuple[str | None, str | None, float | None]
        Country code, country name, and confidence.
    """
    if not domain:
        return None, None, None

    domain = domain.strip().lower().rstrip(".")

    if not domain:
        return None, None, None

    # Handle multi-part ccTLDs such as:
    #
    #     example.co.uk
    #
    # The final label is "uk", which correctly maps to GB.
    try:
        labels = domain.split(".")
    except AttributeError:
        return None, None, None

    if not labels:
        return None, None, None

    tld = labels[-1]

    mapping: dict[str, str] = {
        "uk": "GB",
        "de": "DE",
        "fr": "FR",
        "it": "IT",
        "ca": "CA",
        "au": "AU",
        "cn": "CN",
        "jp": "JP",
        "in": "IN",
        "nl": "NL",
        "be": "BE",
        "ch": "CH",
        "se": "SE",
        "no": "NO",
        "dk": "DK",
        "fi": "FI",
        "pl": "PL",
        "es": "ES",
        "pt": "PT",
        "br": "BR",
        "mx": "MX",
        "nz": "NZ",
        "za": "ZA",
        "sg": "SG",
        "ae": "AE",
        "ie": "IE",
        "at": "AT",
        "cz": "CZ",
        "ro": "RO",
        "hu": "HU",
        "gr": "GR",
        "ua": "UA",
        "tr": "TR",
        "il": "IL",
        "kr": "KR",
        "tw": "TW",
        "hk": "HK",
        "sa": "SA",
    }

    code = mapping.get(tld)

    if code is None:
        return None, None, None

    return (
        code,
        COUNTRIES[code],
        0.62,
    )


def infer_industry(
    text: str | None,
) -> tuple[str | None, str | None, float | None]:
    """Infer industry from descriptive text.

    Parameters
    ----------
    text:
        Company name, description, address, or combined business text.

    Returns
    -------
    tuple[str | None, str | None, float | None]
        Industry code, display name, and confidence.
    """
    if not text:
        return None, None, None

    haystack = text.casefold()

    scores: dict[str, int] = {}

    for code, keywords in INDUSTRY_KEYWORDS.items():
        score = 0

        for keyword in keywords:
            if keyword.casefold() in haystack:
                score += 1

        if score:
            scores[code] = score

    if not scores:
        return None, None, None

    # Highest number of matching keywords wins.
    #
    # Sorting by code provides deterministic behaviour if two
    # industries have exactly the same score.
    best_code = max(
        scores,
        key=lambda code: (
            scores[code],
            code,
        ),
    )

    hits = scores[best_code]

    confidence = min(
        0.55 + 0.08 * hits,
        0.86,
    )

    labels = dict(INDUSTRIES)

    return (
        best_code,
        labels[best_code],
        confidence,
    )


def extract_domain(
    url: str | None,
) -> str | None:
    """Extract a hostname from a website value.

    Parameters
    ----------
    url:
        URL or bare domain.

    Returns
    -------
    str | None
        Normalized hostname.
    """
    if not url:
        return None

    value = url.strip()

    if not value:
        return None

    # urlparse("example.com") treats it as a path.
    # Add a scheme for bare domains.
    parse_value = value

    if "://" not in parse_value:
        parse_value = f"http://{parse_value}"

    try:
        host = urlparse(
            parse_value
        ).hostname
    except ValueError:
        return None

    if not host:
        return None

    return host.lower().rstrip(".")


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _looks_like_domain(
    value: str,
) -> bool:
    """Return whether a value looks like a DNS hostname/domain."""

    value = value.strip().lower()

    if not value:
        return False

    # URLs are obviously not postal addresses.
    if "://" in value:
        return True

    # A domain must contain a dot and have no whitespace.
    if "." not in value:
        return False

    if any(character.isspace() for character in value):
        return False

    # Basic hostname shape.
    return bool(
        re.fullmatch(
            r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?",
            value,
        )
    )


def _contains_phrase(
    text: str,
    phrase: str,
) -> bool:
    """Case-insensitive whole-phrase match."""

    normalized_phrase = phrase.casefold().strip()

    if not normalized_phrase:
        return False

    pattern = (
        r"(?<![A-Za-z])"
        + re.escape(normalized_phrase)
        + r"(?![A-Za-z])"
    )

    return bool(
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
    )