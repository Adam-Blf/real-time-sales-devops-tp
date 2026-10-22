import pytest


def pytest_collection_modifyitems(config, items):
    """Marque chaque test avec son niveau d'après son dossier, pour que `-m unit|integration|e2e` fonctionne."""
    for item in items:
        for level in ("unit", "integration", "e2e"):
            if f"tests/{level}/" in item.nodeid:
                item.add_marker(getattr(pytest.mark, level))
