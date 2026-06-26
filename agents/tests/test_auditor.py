from src.auditor import compute_site_summary, classify_page_type, get_applicable_pillars


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


def test_classify_contact_as_utility():
    assert classify_page_type("https://example.com/contact", "Contact Us", "") == "utility"

def test_classify_blog_post_as_article():
    assert classify_page_type("https://example.com/blog/daycare-tips", "5 Daycare Tips", "") == "article"

def test_classify_homepage():
    assert classify_page_type("https://example.com/", "ChildSpot — Find Childcare", "") == "homepage"

def test_applicable_pillars_utility_only_schema():
    pillars = get_applicable_pillars("utility")
    assert "Schema Markup" in pillars
    assert "Source Citations" not in pillars
    assert "Fact Density" not in pillars

def test_applicable_pillars_article_all_six():
    pillars = get_applicable_pillars("article")
    assert len(pillars) == 6


def test_classify_request_as_utility():
    assert classify_page_type("https://example.com/request", "Request Flowers", "") == "utility"

def test_classify_donate_as_utility():
    assert classify_page_type("https://example.com/donate", "Donate", "") == "utility"

def test_classify_signup_as_utility():
    assert classify_page_type("https://example.com/signup", "Sign Up", "") == "utility"

def test_classify_apply_as_utility():
    assert classify_page_type("https://example.com/apply", "Apply Now", "") == "utility"

def test_classify_register_as_utility():
    assert classify_page_type("https://example.com/register", "Register", "") == "utility"

def test_classify_submit_as_utility():
    assert classify_page_type("https://example.com/submit", "Submit", "") == "utility"
