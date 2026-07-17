import threading
import time

from src import tracker


def _tracking_engine(name, state, lock, delay=0.05):
    def q(prompt):
        with lock:
            state["cur"][name] = state["cur"].get(name, 0) + 1
            state["max"][name] = max(state["max"].get(name, 0), state["cur"][name])
            state["calls"][name] = state["calls"].get(name, 0) + 1
        time.sleep(delay)
        with lock:
            state["cur"][name] -= 1
        return f"{name} says nothing about the brand"

    return {"query": q, "model": f"{name}-model"}


def test_run_tracker_parallelizes_within_a_per_engine_bound(monkeypatch):
    """The tracker must run engine calls concurrently (so a 47-wording client
    finishes in minutes, not 40) while never exceeding a per-engine concurrency
    cap (so we don't trip provider rate limits)."""
    state = {"cur": {}, "max": {}, "calls": {}}
    lock = threading.Lock()
    engines = {
        "e1": _tracking_engine("e1", state, lock),
        "e2": _tracking_engine("e2", state, lock),
    }
    monkeypatch.setattr(tracker, "load_engines", lambda: engines)

    config = {
        "target_queries": [
            {
                "id": f"q{i}",
                "prompt_text": f"prompt {i}",
                "bucket": "awareness",
                "paraphrases": [f"para {i}a", f"para {i}b"],
            }
            for i in range(4)
        ],
        "brand_variations": ["BrandX"],
        "website_domain": "brandx.com",
        "competitors": [],
        "engine_concurrency": 2,
    }

    results, _ = tracker.run_tracker(config)

    # 4 queries x 3 wordings x 2 engines x 1 run each = 24 samples.
    assert len(results) == 24
    assert state["calls"] == {"e1": 12, "e2": 12}

    # Bounded: never more than the configured concurrency per engine.
    assert state["max"]["e1"] <= 2
    assert state["max"]["e2"] <= 2
    # Actually concurrent: it reached the cap (not serialized at 1).
    assert state["max"]["e1"] == 2
    assert state["max"]["e2"] == 2
