from unittest.mock import patch
from src.recommender import should_generate_card, build_card_prompt


def test_should_generate_card_below_threshold():
    assert should_generate_card(45) is True
    assert should_generate_card(59) is True


def test_should_not_generate_card_above_threshold():
    assert should_generate_card(60) is False
    assert should_generate_card(90) is False


def test_build_card_prompt_includes_pillar_and_page():
    prompt = build_card_prompt(
        page_url="https://childspot.ca",
        pillar="Fact Density",
        score=20,
        issues=["Only 0.1 facts per 200 words"],
        page_content="ChildSpot is a great platform for families.",
    )
    assert "Fact Density" in prompt
    assert "childspot.ca" in prompt
    assert "0.1 facts" in prompt
