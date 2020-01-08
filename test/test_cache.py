"""
Test all things related to the ``jedi.cache`` module.
"""

from os import unlink

import pytest
import time

from parso.cache import _NodeCacheItem, save_module, load_module, \
    _get_hashed_path, parser_cache, _load_from_file_system, _save_to_file_system
from parso import load_grammar
from parso import cache
from parso import file_io
from parso import parse


@pytest.fixture()
def isolated_jedi_cache(monkeypatch, tmpdir):
    """
    Set `jedi.settings.cache_directory` to a temporary directory during test.

    Same as `clean_jedi_cache`, but create the temporary directory for
    each test case (scope='function').
    """
    monkeypatch.setattr(cache, '_default_cache_path', str(tmpdir))


def test_modulepickling_change_cache_dir(tmpdir):
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

    hashed_grammar = load_grammar()._hashed
    _save_to_file_system(hashed_grammar, path_1, item_1, cache_path=dir_1)
    parser_cache.clear()
    cached = load_stored_item(hashed_grammar, path_1, item_1, cache_path=dir_1)
    assert cached == item_1.node

    _save_to_file_system(hashed_grammar, path_2, item_2, cache_path=dir_2)
    cached = load_stored_item(hashed_grammar, path_1, item_1, cache_path=dir_2)
    assert cached is None


def load_stored_item(hashed_grammar, path, item, cache_path):
    """Load `item` stored at `path` in `cache`."""
    item = _load_from_file_system(hashed_grammar, path, item.change_time - 1, cache_path)
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
    io = file_io.FileIO(path)

    save_module(grammar._hashed, io, module, lines=[])
    assert load_module(grammar._hashed, io) == module

    unlink(_get_hashed_path(grammar._hashed, path))
    parser_cache.clear()

    cached2 = load_module(grammar._hashed, io)
    assert cached2 is None


def test_cache_limit():
    def cache_size():
        return sum(len(v) for v in parser_cache.values())

    try:
        parser_cache.clear()
        future_node_cache_item = _NodeCacheItem('bla', [], change_time=time.time() + 10e6)
        old_node_cache_item = _NodeCacheItem('bla', [], change_time=time.time() - 10e4)
        parser_cache['some_hash_old'] = {
            '/path/%s' % i: old_node_cache_item for i in range(300)
        }
        parser_cache['some_hash_new'] = {
            '/path/%s' % i: future_node_cache_item for i in range(300)
        }
        assert cache_size() == 600
        parse('somecode', cache=True, path='/path/somepath')
        assert cache_size() == 301
    finally:
        parser_cache.clear()


class _FixedTimeFileIO(file_io.KnownContentFileIO):
    def __init__(self, path, content, last_modified):
        super(_FixedTimeFileIO, self).__init__(path, content)
        self._last_modified = last_modified

    def get_last_modified(self):
        return self._last_modified


@pytest.mark.parametrize('diff_cache', [False, True])
@pytest.mark.parametrize('use_file_io', [False, True])
def test_cache_last_used_update(diff_cache, use_file_io):
    p = '/path/last-used'
    parser_cache.clear()  # Clear, because then it's easier to find stuff.
    parse('somecode', cache=True, path=p)
    node_cache_item = next(iter(parser_cache.values()))[p]
    now = time.time()
    assert node_cache_item.last_used < now

    if use_file_io:
        f = _FixedTimeFileIO(p, 'code', node_cache_item.last_used - 10)
        parse(file_io=f, cache=True, diff_cache=diff_cache)
    else:
        parse('somecode2', cache=True, path=p, diff_cache=diff_cache)

    node_cache_item = next(iter(parser_cache.values()))[p]
    assert now < node_cache_item.last_used < time.time()
