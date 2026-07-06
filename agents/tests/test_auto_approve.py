from src.improvement.auto_approve import compute_eligible_action_types, apply_auto_approve


def _card(action_type, status, run_id, track="automated"):
    return {"action_type": action_type, "status": status, "run_id": run_id, "track": track}


class TestComputeEligibleActionTypes:
    def test_three_clean_cycles_earn_eligibility(self):
        history = [
            _card("add_faq_schema", "implemented", "r1"),
            _card("add_faq_schema", "approved", "r2"),
            _card("add_faq_schema", "implemented", "r3"),
        ]
        assert "add_faq_schema" in compute_eligible_action_types(history, min_cycles=3)

    def test_two_cycles_not_enough(self):
        history = [
            _card("add_faq_schema", "implemented", "r1"),
            _card("add_faq_schema", "implemented", "r2"),
        ]
        assert compute_eligible_action_types(history, min_cycles=3) == set()

    def test_any_rejection_ever_blocks_eligibility(self):
        history = [
            _card("fix_schema", "implemented", "r1"),
            _card("fix_schema", "rejected", "r2"),
            _card("fix_schema", "implemented", "r3"),
            _card("fix_schema", "implemented", "r4"),
        ]
        assert "fix_schema" not in compute_eligible_action_types(history, min_cycles=3)

    def test_pending_cards_do_not_count_as_clean_cycles(self):
        history = [
            _card("add_faq_schema", "implemented", "r1"),
            _card("add_faq_schema", "pending", "r2"),
            _card("add_faq_schema", "implemented", "r3"),
        ]
        assert "add_faq_schema" not in compute_eligible_action_types(history, min_cycles=3)

    def test_content_action_types_never_eligible_from_history(self):
        history = [_card("restructure_intro", "implemented", f"r{i}") for i in range(10)]
        assert "restructure_intro" not in compute_eligible_action_types(history, min_cycles=3)


class TestApplyAutoApprove:
    def test_eligible_valid_automated_card_gets_auto_approved(self):
        cards = [{"action_type": "add_faq_schema", "track": "automated",
                  "validation_passed": True, "status": "pending"}]
        n = apply_auto_approve(cards, {"add_faq_schema"})
        assert n == 1
        assert cards[0]["status"] == "approved"
        assert cards[0]["auto_approved"] is True

    def test_ineligible_type_stays_pending(self):
        cards = [{"action_type": "restructure_intro", "track": "automated",
                  "validation_passed": True, "status": "pending"}]
        assert apply_auto_approve(cards, {"add_faq_schema"}) == 0
        assert cards[0]["status"] == "pending"

    def test_failed_validation_never_auto_approved(self):
        cards = [{"action_type": "add_faq_schema", "track": "automated",
                  "validation_passed": False, "status": "pending"}]
        assert apply_auto_approve(cards, {"add_faq_schema"}) == 0

    def test_manual_track_never_auto_approved(self):
        cards = [{"action_type": "add_faq_schema", "track": "manual",
                  "validation_passed": True, "status": "pending"}]
        assert apply_auto_approve(cards, {"add_faq_schema"}) == 0
