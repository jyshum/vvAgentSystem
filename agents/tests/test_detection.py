import pytest

from src.detection import detect_brand, detect_competitors


@pytest.fixture(autouse=True)
def mock_classify(monkeypatch):
    monkeypatch.setattr(
        "src.detection.classify_mention_level",
        lambda text, brand: {"mention_level": 2, "mention_level_label": "listed_with_context"},
    )


class TestDetectBrand:
    def test_brand_mentioned_exact_match(self):
        text = "ChildSpot is a popular childcare platform in Ontario."
        result = detect_brand(text, ["ChildSpot", "Child Spot"], "childspot.ca")
        assert result["brand_mentioned"] is True
        assert result["brand_cited"] is False
        assert result["citation_url"] is None

    def test_brand_mentioned_case_insensitive(self):
        text = "You might want to check out childspot for daycare listings."
        result = detect_brand(text, ["ChildSpot"], "childspot.ca")
        assert result["brand_mentioned"] is True

    def test_brand_mentioned_variation(self):
        text = "Child Spot is a helpful resource for parents."
        result = detect_brand(text, ["ChildSpot", "Child Spot"], "childspot.ca")
        assert result["brand_mentioned"] is True

    def test_brand_not_mentioned(self):
        text = "There are several government resources for finding daycare."
        result = detect_brand(text, ["ChildSpot", "Child Spot"], "childspot.ca")
        assert result["brand_mentioned"] is False
        assert result["brand_cited"] is False

    def test_brand_cited_with_url(self):
        text = "You can find daycare at https://childspot.ca/search which lists providers."
        result = detect_brand(text, ["ChildSpot"], "childspot.ca")
        assert result["brand_mentioned"] is True
        assert result["brand_cited"] is True
        assert result["citation_url"] == "https://childspot.ca/search"

    def test_brand_cited_with_url_in_markdown(self):
        text = "Check [ChildSpot](https://www.childspot.ca) for listings."
        result = detect_brand(text, ["ChildSpot"], "childspot.ca")
        assert result["brand_mentioned"] is True
        assert result["brand_cited"] is True
        assert "childspot.ca" in result["citation_url"]

    def test_domain_mention_counts_as_citation(self):
        text = "Visit childspot.ca for Ontario daycare options."
        result = detect_brand(text, ["ChildSpot"], "childspot.ca")
        assert result["brand_mentioned"] is True
        assert result["brand_cited"] is True


class TestDetectCompetitors:
    def test_single_competitor_found(self):
        text = "OneList Ontario is the government's official waitlist system."
        result = detect_competitors(text, ["OneList Ontario", "HiMama"])
        assert result == ["OneList Ontario"]

    def test_multiple_competitors_found(self):
        text = "Alternatives include OneList Ontario and HiMama for tracking."
        result = detect_competitors(text, ["OneList Ontario", "HiMama"])
        assert "OneList Ontario" in result
        assert "HiMama" in result

    def test_no_competitors_found(self):
        text = "There are various childcare platforms available."
        result = detect_competitors(text, ["OneList Ontario", "HiMama"])
        assert result == []

    def test_competitor_case_insensitive(self):
        text = "himama is a popular daycare management app."
        result = detect_competitors(text, ["HiMama"])
        assert result == ["HiMama"]
