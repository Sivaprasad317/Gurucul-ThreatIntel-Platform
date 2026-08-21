from bs4 import BeautifulSoup
from backend.app.extractors.base import CandidateVictim


class QilinExtractor:
    parser_key = "qilin"

    def extract(self, html: str, source_page: str) -> list[CandidateVictim]:
        soup = BeautifulSoup(html, "html.parser")
        result = []
        for item in soup.find_all("div", class_="item_box"):
            title = item.find("a", class_="item_box-title mb-2 mt-1") or item.find("a")
            if not title:
                continue
            name = title.get_text(" ", strip=True)
            if not name:
                continue
            p = item.find("p")
            result.append(CandidateVictim(
                name=name,
                description=p.get_text(" ", strip=True) if p else None,
                source_page=str(title.get("href") or source_page),
            ))
        return result


EXTRACTOR = QilinExtractor()
