import os
import sys


ENGINES = {}


def _try_register(name: str, module_path: str, env_var: str, model: str) -> None:
    if not os.environ.get(env_var):
        print(f"  [SKIP] {name}: {env_var} not set", file=sys.stderr)
        return
    try:
        import importlib
        mod = importlib.import_module(module_path)
        ENGINES[name] = {"query": mod.query, "model": model}
    except Exception as e:
        print(f"  [SKIP] {name}: failed to load — {e}", file=sys.stderr)


def load_engines() -> dict:
    ENGINES.clear()
    _try_register("chatgpt", "src.engines.chatgpt", "OPENAI_API_KEY", "gpt-4o-mini")
    _try_register("perplexity", "src.engines.perplexity", "PERPLEXITY_API_KEY", "sonar")
    _try_register("claude", "src.engines.claude", "ANTHROPIC_API_KEY", "claude-haiku-4-5")
    _try_register("gemini", "src.engines.gemini", "GOOGLE_GEMINI_API_KEY", "gemini-2.5-flash")
    return ENGINES
