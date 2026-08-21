from backend.app.services.normalization import country_from_value, infer_country_from_domain, infer_industry


def test_country_normalization():
    assert country_from_value("United States") == ("US", "United States", 1.0)
    assert country_from_value("DE") == ("DE", "Germany", 1.0)


def test_cc_tld_is_not_ground_truth():
    code, name, confidence = infer_country_from_domain("example.de")
    assert code == "DE"
    assert confidence < 1.0


def test_industry_inference_is_explicitly_confidence_limited():
    code, name, confidence = infer_industry("regional manufacturing company")
    assert code == "manufacturing"
    assert confidence < 1.0
