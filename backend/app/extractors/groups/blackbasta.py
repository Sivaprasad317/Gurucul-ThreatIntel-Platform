from bs4 import BeautifulSoup
from backend.app.extractors.base import CandidateVictim


class BlackBastaExtractor:
    parser_key = "blackbasta"

    def extract(self, html: str, source_page: str) -> list[CandidateVictim]:
        soup = BeautifulSoup(html, "html.parser")
        result = []
        for card in soup.find_all("div", class_="card"):
            title = card.find("a", class_="blog_name_link") or card.find("a")
            if not title:
                continue
            name = title.get_text(" ", strip=True)
            if not name:
                continue
            paragraphs = card.find_all("p")
            result.append(CandidateVictim(
                name=name,
                description=" ".join(p.get_text(" ", strip=True) for p in paragraphs) or None,
                source_page=source_page,
            ))
        return result


EXTRACTOR = BlackBastaExtractor()
