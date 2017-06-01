import tempfile
import shutil
import logging
import sys

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


def pytest_addoption(parser):
    parser.addoption("--logging", "-L", action='store_true',
                     help="Enables the logging output.")


def pytest_configure(config):
    if config.option.logging:
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)

        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        #formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        #ch.setFormatter(formatter)

        root.addHandler(ch)
