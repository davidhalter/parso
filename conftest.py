import tempfile
import shutil

import pytest

from parso import cache


#collect_ignore = ["setup.py"]


# The following hooks (pytest_configure, pytest_unconfigure) are used
# to modify `cache._default_cache_path` because `clean_parso_cache`
# has no effect during doctests.  Without these hooks, doctests uses
# user's cache (e.g., ~/.cache/parso/).  We should remove this
# workaround once the problem is fixed in py.test.
#
# See (this was back when parso was part of jedi):
# - https://github.com/davidhalter/jedi/pull/168
# - https://bitbucket.org/hpk42/pytest/issue/275/

parso_cache_directory_orig = None
parso_cache_directory_temp = None


def pytest_addoption(parser):
    parser.addoption("--warning-is-error", action='store_true',
                     help="Warnings are treated as errors.")


def pytest_configure(config):
    global parso_cache_directory_orig, parso_cache_directory_temp
    parso_cache_directory_orig = cache._default_cache_path
    parso_cache_directory_temp = tempfile.mkdtemp(prefix='parso-test-')
    cache._default_cache_path = parso_cache_directory_temp

    if config.option.warning_is_error:
        import warnings
        warnings.simplefilter("error")


def pytest_unconfigure(config):
    global parso_cache_directory_orig, parso_cache_directory_temp
    cache._default_cache_path = parso_cache_directory_orig
    shutil.rmtree(parso_cache_directory_temp)


@pytest.fixture(scope='session')
def clean_parso_cache(request):
    """
    Set `jedi.settings.cache_directory` to a temporary directory during test.

    Note that you can't use built-in `tmpdir` and `monkeypatch`
    fixture here because their scope is 'function', which is not used
    in 'session' scope fixture.

    This fixture is activated in ../pytest.ini.
    """
    from jedi import settings
    old = settings.cache_directory
    tmp = tempfile.mkdtemp(prefix='jedi-test-')
    settings.cache_directory = tmp

    @request.addfinalizer
    def restore():
        settings.cache_directory = old
        shutil.rmtree(tmp)
