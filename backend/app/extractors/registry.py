from backend.app.extractors.groups.blackbasta import EXTRACTOR as BLACKBASTA
from backend.app.extractors.groups.dragonforce import EXTRACTOR as DRAGONFORCE
from backend.app.extractors.groups.qilin import EXTRACTOR as QILIN

EXTRACTORS = {e.parser_key: e for e in (DRAGONFORCE, QILIN, BLACKBASTA)}


class ExtractorNotFoundError(LookupError):
    pass


def available_extractors() -> list[str]:
    return sorted(EXTRACTORS)


def get_extractor(parser_key: str):
    try:
        return EXTRACTORS[parser_key]
    except KeyError as exc:
        raise ExtractorNotFoundError(f"No extractor installed for parser '{parser_key}'.") from exc
