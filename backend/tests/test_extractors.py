from backend.app.extractors.groups.qilin import QilinExtractor
from backend.app.extractors.groups.blackbasta import BlackBastaExtractor


def test_qilin():
    html = '<div class="item_box"><a class="item_box-title mb-2 mt-1" href="/x">Acme</a><p>Manufacturing company</p></div>'
    result = QilinExtractor().extract(html, "https://example.invalid")
    assert len(result) == 1 and result[0].name == "Acme"


def test_blackbasta():
    html = '<div class="card"><a class="blog_name_link">Acme</a><p>Company</p></div>'
    result = BlackBastaExtractor().extract(html, "https://example.invalid")
    assert len(result) == 1 and result[0].name == "Acme"
