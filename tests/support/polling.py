"""Attente d'une condition avec délai maximal, au lieu d'un sleep fixe."""

import time


class PollingTimeout(AssertionError):
    pass


def wait_for(probe, timeout: float, interval: float = 1.0, description: str = "condition"):
    """Appelle probe() jusqu'à obtenir une valeur vraie, ou échoue une fois le délai dépassé."""
    deadline = time.monotonic() + timeout
    last_error = None
    while True:
        try:
            result = probe()
            if result:
                return result
        except Exception as error:  # le service n'est peut-être pas encore prêt, on continue
            last_error = error
        if time.monotonic() >= deadline:
            detail = f" (last error: {last_error!r})" if last_error else ""
            raise PollingTimeout(f"Timed out after {timeout:.0f}s waiting for {description}{detail}")
        time.sleep(interval)
