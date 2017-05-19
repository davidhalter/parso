"""
Test all things related to the ``jedi.cache`` module.
"""

from os import unlink

import pytest

from parso.cache import _NodeCacheItem, save_module, load_module, \
    _get_hashed_path, parser_cache, _load_from_file_system, _save_to_file_system
from parso.python import load_grammar
from parso import cache


@pytest.fixture()
def isolated_jedi_cache(monkeypatch, tmpdir):
    """
    Set `jedi.settings.cache_directory` to a temporary directory during test.

    Same as `clean_jedi_cache`, but create the temporary directory for
    each test case (scope='function').
    """
    monkeypatch.setattr(cache, '_default_cache_path', str(tmpdir))


def test_modulepickling_change_cache_dir(monkeypatch, tmpdir):
    """
    ParserPickling should not save old cache when cache_directory is changed.

    See: `#168 <https://github.com/davidhalter/jedi/pull/168>`_
    """
    dir_1 = str(tmpdir.mkdir('first'))
    dir_2 = str(tmpdir.mkdir('second'))

    item_1 = _NodeCacheItem('bla', [])
    item_2 = _NodeCacheItem('bla', [])
    path_1 = 'fake path 1'
    path_2 = 'fake path 2'

    monkeypatch.setattr(cache, '_default_cache_path', dir_1)
    grammar = load_grammar()
    _save_to_file_system(grammar, path_1, item_1)
    parser_cache.clear()
    cached = load_stored_item(grammar, path_1, item_1)
    assert cached == item_1.node

    monkeypatch.setattr(cache, '_default_cache_path', dir_2)
    _save_to_file_system(grammar, path_2, item_2)
    cached = load_stored_item(grammar, path_1, item_1)
    assert cached is None


def load_stored_item(grammar, path, item):
    """Load `item` stored at `path` in `cache`."""
    item = _load_from_file_system(grammar, path, item.change_time - 1)
    return item


@pytest.mark.usefixtures("isolated_jedi_cache")
def test_modulepickling_simulate_deleted_cache(tmpdir):
    """
    Tests loading from a cache file after it is deleted.
    According to macOS `dev docs`__,

        Note that the system may delete the Caches/ directory to free up disk
        space, so your app must be able to re-create or download these files as
        needed.

    It is possible that other supported platforms treat cache files the same
    way.

    __ https://developer.apple.com/library/content/documentation/FileManagement/Conceptual/FileSystemProgrammingGuide/FileSystemOverview/FileSystemOverview.html
    """
    grammar = load_grammar()
    module = 'fake parser'

    # Create the file
    path = tmpdir.dirname + '/some_path'
    with open(path, 'w'):
        pass

    save_module(grammar, path, module, [])
    assert load_module(grammar, path) == module

    unlink(_get_hashed_path(grammar, path))
    parser_cache.clear()

    cached2 = load_module(grammar, path)
    assert cached2 is None
