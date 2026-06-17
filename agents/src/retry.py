import time
import functools


def with_retries(max_retries: int = 3, base_delay: float = 2.0):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        print(f"    retry {attempt + 1}/{max_retries} in {delay:.0f}s — {e}")
                        time.sleep(delay)
            raise last_error
        return wrapper
    return decorator
