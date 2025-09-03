import os
import sys
from functools import wraps
from slowapi import Limiter
from slowapi.util import get_remote_address

# Flag used only during pytest to explicitly enable real rate limiting in tests
TEST_RATE_LIMITS_ENABLED = False

# Check if we're running in a test environment
def is_testing():
    return (
        os.getenv("PYTEST_CURRENT_TEST") is not None or
        "pytest" in sys.modules or
        (sys.argv and "pytest" in sys.argv[0])
    )

def enable_test_rate_limits():
    """Enable real rate limiting inside tests (used by explicit rate limit tests).

    Also resets the in-memory limiter storage by creating a fresh Limiter instance so
    previous test traffic doesn't cause immediate 429 responses.
    """
    global TEST_RATE_LIMITS_ENABLED, limiter
    TEST_RATE_LIMITS_ENABLED = True
    # Re-create limiter so counters start clean per explicit rate limit test
    limiter = Limiter(key_func=get_remote_address)

def disable_test_rate_limits():
    """Disable real rate limiting inside tests (default)."""
    global TEST_RATE_LIMITS_ENABLED
    TEST_RATE_LIMITS_ENABLED = False

# Base limiter (production defaults). We intentionally do NOT inflate limits here; instead we bypass
# enforcement in decorators unless explicitly enabled via the flag above.
limiter = Limiter(key_func=get_remote_address)

def conditional_limit(limit_str: str):
    """Production: apply limiter immediately. Tests: no-op unless enabled via flag."""
    def decorator(func):
        if not is_testing():
            return limiter.limit(limit_str)(func)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            if TEST_RATE_LIMITS_ENABLED:
                limited = getattr(wrapper, "_limited_func", None)
                if limited is None:
                    limited = limiter.limit(limit_str)(func)
                    wrapper._limited_func = limited
                return await limited(*args, **kwargs)
            return await func(*args, **kwargs)
        return wrapper
    return decorator

__all__ = [
    "limiter",
    "conditional_limit",
    "enable_test_rate_limits",
    "disable_test_rate_limits",
    "is_testing",
    "reset_rate_limit_wrappers",
]

def reset_rate_limit_wrappers(*funcs):
    """Remove cached limited wrapper state for the given functions (test helper)."""
    for f in funcs:
        if f and hasattr(f, "_limited_func"):
            try:
                delattr(f, "_limited_func")
            except AttributeError:
                pass
