import tempfile
import shutil

import pytest

from parso import cache


collect_ignore = ["setup.py"]

@pytest.fixture(scope='session')
def clean_parso_cache():
    """
    Set the default cache directory to a temporary directory during tests.

    Note that you can't use built-in `tmpdir` and `monkeypatch`
    fixture here because their scope is 'function', which is not used
    in 'session' scope fixture.

    This fixture is activated in ../pytest.ini.
    """
    old = cache._default_cache_path
    tmp = tempfile.mkdtemp(prefix='parso-test-')
    cache._default_cache_path = tmp
    yield
    cache._default_cache_path = old
    shutil.rmtree(tmp)
