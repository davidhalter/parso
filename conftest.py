import tempfile
import shutil

import pytest

from parso import cache


collect_ignore = ["setup.py"]


def pytest_addoption(parser):
    parser.addoption("--warning-is-error", action='store_true',
                     help="Warnings are treated as errors.")


def pytest_configure(config):
    if config.option.warning_is_error:
        import warnings
        warnings.simplefilter("error")


@pytest.fixture(scope='session')
def clean_parso_cache(request):
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

    @request.addfinalizer
    def restore():
        cache._default_cache_path = old
        shutil.rmtree(tmp)
