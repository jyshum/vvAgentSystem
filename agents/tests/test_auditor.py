from src.auditor import compute_site_summary


def test_compute_site_summary_calculates_averages():
    pages = [
        {
            "url": "https://childspot.ca",
            "title": "Home",
            "word_count": 500,
            "total_score": 40,
            "pillars": {
                "Content Structure": {"score": 30},
                "Fact Density": {"score": 20},
                "Source Citations": {"score": 60},
                "Authority Signals": {"score": 10},
                "Schema Markup": {"score": 80},
                "Freshness": {"score": 40},
            }
        },
        {
            "url": "https://childspot.ca/how-it-works",
            "title": "How It Works",
            "word_count": 800,
            "total_score": 70,
            "pillars": {
                "Content Structure": {"score": 70},
                "Fact Density": {"score": 60},
                "Source Citations": {"score": 80},
                "Authority Signals": {"score": 50},
                "Schema Markup": {"score": 100},
                "Freshness": {"score": 60},
            }
        }
    ]

    summary = compute_site_summary(pages)

    assert summary["pages_audited"] == 2
    assert summary["site_score"] == 55
    assert summary["pillar_averages"]["Content Structure"] == 50
    assert summary["weakest_pillar"] == "Authority Signals"
    assert len(summary["weakest_pages"]) <= 3
