"""Wait for a condition with a deadline instead of a fixed sleep."""

import time


class PollingTimeout(AssertionError):
    pass


def wait_for(probe, timeout: float, interval: float = 1.0, description: str = "condition"):
    """Call probe() until it returns a truthy value, or fail once the timeout expires."""
    deadline = time.monotonic() + timeout
    last_error = None
    while True:
        try:
            result = probe()
            if result:
                return result
        except Exception as error:  # the service may not be ready yet, keep polling
            last_error = error
        if time.monotonic() >= deadline:
            detail = f" (last error: {last_error!r})" if last_error else ""
            raise PollingTimeout(f"Timed out after {timeout:.0f}s waiting for {description}{detail}")
        time.sleep(interval)
