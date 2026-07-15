import pytest

from src.technical_audit.site import SiteIdentity


def test_bare_and_www_hosts_are_same_site():
    identity = SiteIdentity.from_domain("budgetyourmd.ca", "squarespace")
    identity = identity.with_final_homepage("https://www.budgetyourmd.ca/")

    assert identity.configured_domain == "budgetyourmd.ca"
    assert identity.platform == "squarespace"
    assert identity.allows("https://budgetyourmd.ca/")
    assert identity.allows("https://www.budgetyourmd.ca/")


def test_site_identity_rejects_non_https_credentials_ports_and_other_hosts():
    identity = SiteIdentity.from_domain("https://budgetyourmd.ca/", "squarespace")

    assert not identity.allows("http://budgetyourmd.ca/")
    assert not identity.allows("https://budgetyourmd.ca.evil.example/")
    assert not identity.allows("https://user:secret@budgetyourmd.ca/")
    assert not identity.allows("https://budgetyourmd.ca:8443/")


def test_site_identity_normalizes_www_configuration_to_one_host_pair():
    identity = SiteIdentity.from_domain("WWW.BudgetYourMD.ca", " Squarespace ")

    assert identity.configured_domain == "www.budgetyourmd.ca"
    assert identity.platform == "squarespace"
    assert identity.allowed_hosts == frozenset(
        {"budgetyourmd.ca", "www.budgetyourmd.ca"}
    )


@pytest.mark.parametrize(
    "domain",
    ["https://example.com:8443", "localhost", "127.0.0.1", "[::1]"],
)
def test_site_identity_rejects_non_public_or_nonstandard_configured_hosts(domain):
    with pytest.raises(ValueError, match="public hostname"):
        SiteIdentity.from_domain(domain, "other")
