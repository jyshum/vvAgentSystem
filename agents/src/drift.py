import hashlib
import json


def compute_query_set_signature(intents: list[dict]) -> str:
    """Hash the active intent set for cycle-over-cycle comparability checks."""
    parts = []
    for q in intents:
        slug = q.get("slug") or q.get("prompt_text", "")
        version = q.get("version", 1)
        canonical = q.get("prompt_text", "")
        paraphrases = sorted(q.get("paraphrases") or [])
        inner = hashlib.sha256(
            json.dumps([canonical, paraphrases], sort_keys=True).encode()
        ).hexdigest()
        parts.append(f"{slug}:{version}:{inner}")
    joined = "\n".join(sorted(parts))
    return hashlib.sha256(joined.encode()).hexdigest()
