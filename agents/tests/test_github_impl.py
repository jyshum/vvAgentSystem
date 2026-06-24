from src.implementors.github_impl import build_branch_name, build_pr_body


def test_build_branch_name_is_slugified():
    name = build_branch_name("Schema Markup", "https://childspot.ca/how-it-works")
    assert " " not in name
    assert "schema" in name.lower()
    assert name.startswith("vv-audit-")


def test_build_pr_body_includes_before_and_after():
    body = build_pr_body(
        pillar="Fact Density",
        page_url="https://childspot.ca",
        issue="Only 0.1 facts per 200 words",
        before_text="ChildSpot is great for families.",
        after_text="73% of Ontario parents spend 12+ months finding childcare. ChildSpot cuts that to 2 weeks.",
    )
    assert "Fact Density" in body
    assert "73%" in body
    assert "childspot.ca" in body
