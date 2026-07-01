from unittest.mock import patch
from src.detection import classify_mention_level, detect_brand


class TestClassifyMentionLevel:
    def test_returns_primary_recommendation(self):
        with patch("src.detection._call_haiku", return_value="primary_recommendation"):
            result = classify_mention_level("The best tool is BrandX.", "BrandX")
        assert result == {"mention_level": 4, "mention_level_label": "primary_recommendation"}

    def test_returns_recommended(self):
        with patch("src.detection._call_haiku", return_value="recommended"):
            result = classify_mention_level("I recommend BrandX for this.", "BrandX")
        assert result == {"mention_level": 3, "mention_level_label": "recommended"}

    def test_returns_listed_with_context(self):
        with patch("src.detection._call_haiku", return_value="listed_with_context"):
            result = classify_mention_level("BrandX offers a budget template.", "BrandX")
        assert result == {"mention_level": 2, "mention_level_label": "listed_with_context"}

    def test_returns_passing_mention(self):
        with patch("src.detection._call_haiku", return_value="passing_mention"):
            result = classify_mention_level("Resources include BrandX and others.", "BrandX")
        assert result == {"mention_level": 1, "mention_level_label": "passing_mention"}

    def test_unexpected_response_defaults_to_passing(self):
        with patch("src.detection._call_haiku", return_value="something_weird"):
            result = classify_mention_level("BrandX is here.", "BrandX")
        assert result == {"mention_level": 1, "mention_level_label": "passing_mention"}

    def test_haiku_failure_defaults_to_passing(self):
        with patch("src.detection._call_haiku", side_effect=Exception("API error")):
            result = classify_mention_level("BrandX is here.", "BrandX")
        assert result == {"mention_level": 1, "mention_level_label": "passing_mention"}


class TestDetectBrandWithLevel:
    def test_not_mentioned_returns_level_zero(self):
        result = detect_brand("No brands here.", ["BrandX"], "brandx.com")
        assert result["mention_level"] == 0
        assert result["mention_level_label"] == "not_mentioned"

    def test_mentioned_includes_level(self):
        with patch("src.detection.classify_mention_level",
                    return_value={"mention_level": 3, "mention_level_label": "recommended"}):
            result = detect_brand("BrandX is great.", ["BrandX"], "brandx.com")
        assert result["mention_level"] == 3
        assert result["mention_level_label"] == "recommended"
