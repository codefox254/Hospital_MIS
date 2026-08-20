import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_cache():
    """
    DRF's throttle classes persist state in Django's cache backend, which
    otherwise leaks between tests within the same run (e.g. a throttling
    test tripping the 'auth' scope for every test that follows it).
    """
    cache.clear()
    yield
    cache.clear()
