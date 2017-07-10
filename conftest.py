import re
import tempfile
import shutil
import logging
import sys
import os

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


def pytest_generate_tests(metafunc):
    if 'normalizer_issue_case' in metafunc.fixturenames:
        base_dir = os.path.join(os.path.dirname(__file__), 'test', 'normalizer_issue_files')

        cases = list(colllect_normalizer_tests(base_dir))
        metafunc.parametrize(
            'normalizer_issue_case',
            cases,
            ids=[c.name for c in cases]
        )


class NormalizerIssueCase(object):
    """
    Static Analysis cases lie in the static_analysis folder.
    The tests also start with `#!`, like the goto_definition tests.
    """
    def __init__(self, path):
        self.path = path
        self.name = os.path.basename(path)
        match = re.search(r'python([\d.]+)\.py', self.name)
        self.python_version = match and match.group(1)


def colllect_normalizer_tests(base_dir):
    for f_name in os.listdir(base_dir):
        if f_name.endswith(".py"):
            path = os.path.join(base_dir, f_name)
            yield NormalizerIssueCase(path)


def pytest_configure(config):
    if config.option.logging:
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)

        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        #formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        #ch.setFormatter(formatter)

        root.addHandler(ch)
