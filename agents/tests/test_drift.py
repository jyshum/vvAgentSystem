from src.drift import compute_query_set_signature


def _intent(slug, version=1, paraphrases=None, prompt="p"):
    return {"slug": slug, "version": version, "prompt_text": prompt, "paraphrases": paraphrases or []}


def test_signature_stable_for_same_set_regardless_of_order():
    a = [_intent("x", paraphrases=["a", "b"]), _intent("y")]
    b = [_intent("y"), _intent("x", paraphrases=["b", "a"])]  # reordered intents + paraphrases
    assert compute_query_set_signature(a) == compute_query_set_signature(b)


def test_signature_changes_when_paraphrase_edited():
    a = [_intent("x", paraphrases=["a", "b"])]
    b = [_intent("x", paraphrases=["a", "c"])]
    assert compute_query_set_signature(a) != compute_query_set_signature(b)


def test_signature_changes_when_intent_added_or_removed():
    a = [_intent("x")]
    b = [_intent("x"), _intent("y")]
    assert compute_query_set_signature(a) != compute_query_set_signature(b)


def test_signature_changes_on_version_bump():
    a = [_intent("x", version=1)]
    b = [_intent("x", version=2)]
    assert compute_query_set_signature(a) != compute_query_set_signature(b)


def test_empty_set_is_stable():
    assert compute_query_set_signature([]) == compute_query_set_signature([])
