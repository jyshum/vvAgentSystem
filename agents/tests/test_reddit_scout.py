from unittest.mock import patch, MagicMock
from src.reddit_scout import build_search_url, parse_reddit_results, score_relevance


def test_build_search_url_encodes_query():
    url = build_search_url("childspot daycare canada")
    assert "childspot" in url
    assert "reddit.com/search.json" in url


def test_parse_reddit_results_extracts_posts():
    mock_json = {
        "data": {
            "children": [
                {
                    "data": {
                        "title": "Best daycare apps in Ontario",
                        "url": "https://reddit.com/r/ontario/123",
                        "subreddit": "ontario",
                        "score": 42,
                        "num_comments": 15,
                        "selftext": "Looking for recommendations for daycare apps...",
                        "permalink": "/r/ontario/comments/123/best_daycare/",
                    }
                }
            ]
        }
    }
    posts = parse_reddit_results(mock_json)
    assert len(posts) == 1
    assert posts[0]["title"] == "Best daycare apps in Ontario"
    assert posts[0]["subreddit"] == "ontario"
    assert posts[0]["score"] == 42


def test_score_relevance_higher_for_brand_match():
    post = {
        "title": "Anyone used ChildSpot to find daycare?",
        "selftext": "My friend mentioned ChildSpot",
    }
    score = score_relevance(post, brand_name="ChildSpot", keywords=["daycare", "childcare"])
    assert score > 0.5
