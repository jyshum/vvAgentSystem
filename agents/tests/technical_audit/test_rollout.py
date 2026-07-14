import pytest

from src.technical_audit.rollout import AuditRolloutPolicy


def test_defaults_are_off_and_allow_nobody(monkeypatch):
    monkeypatch.delenv("TECHNICAL_AUDIT_V1_ENABLED", raising=False)
    monkeypatch.delenv("TECHNICAL_AUDIT_INTERNAL_CLIENT_IDS", raising=False)
    monkeypatch.delenv("TECHNICAL_AUDIT_CHECK_SETS", raising=False)

    policy = AuditRolloutPolicy.from_environment()

    assert policy.enabled is False
    assert policy.client_ids == frozenset()
    assert policy.check_sets == ("foundation",)
    assert policy.active_for("client-1") is False


def test_enabled_requires_explicit_client_membership(monkeypatch):
    monkeypatch.setenv("TECHNICAL_AUDIT_V1_ENABLED", "true")
    monkeypatch.setenv(
        "TECHNICAL_AUDIT_INTERNAL_CLIENT_IDS", "client-1, client-2"
    )

    policy = AuditRolloutPolicy.from_environment()

    assert policy.active_for("client-1") is True
    assert policy.active_for("client-3") is False


def test_star_explicitly_enables_all_clients(monkeypatch):
    monkeypatch.setenv("TECHNICAL_AUDIT_V1_ENABLED", "true")
    monkeypatch.setenv("TECHNICAL_AUDIT_INTERNAL_CLIENT_IDS", "*")

    assert AuditRolloutPolicy.from_environment().active_for("any-client") is True


def test_only_available_check_sets_are_accepted(monkeypatch):
    monkeypatch.setenv("TECHNICAL_AUDIT_CHECK_SETS", "foundation,protocol")

    with pytest.raises(ValueError, match="Unavailable technical audit check set"):
        AuditRolloutPolicy.from_environment()
