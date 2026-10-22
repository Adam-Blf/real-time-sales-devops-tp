import pytest


def pytest_collection_modifyitems(config, items):
    """Tag each test with its level from its folder, so `-m unit|integration|e2e` works."""
    for item in items:
        for level in ("unit", "integration", "e2e"):
            if f"tests/{level}/" in item.nodeid:
                item.add_marker(getattr(pytest.mark, level))
