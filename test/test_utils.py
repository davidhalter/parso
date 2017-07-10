from codecs import BOM_UTF8

from parso.utils import splitlines, source_to_unicode
import parso


def test_splitlines_no_keepends():
    assert splitlines('asd\r\n') == ['asd', '']
    assert splitlines('asd\r\n\f') == ['asd', '\f']
    assert splitlines('\fasd\r\n') == ['\fasd', '']
    assert splitlines('') == ['']
    assert splitlines('\n') == ['', '']


def test_splitlines_keepends():
    assert splitlines('asd\r\n', keepends=True) == ['asd\r\n', '']
    assert splitlines('asd\r\n\f', keepends=True) == ['asd\r\n', '\f']
    assert splitlines('\fasd\r\n', keepends=True) == ['\fasd\r\n', '']
    assert splitlines('', keepends=True) == ['']
    assert splitlines('\n', keepends=True) == ['\n', '']


def test_source_to_unicode_unicode_text():
    source = (
        b"# vim: fileencoding=utf-8\n"
        b"# \xe3\x81\x82\xe3\x81\x84\xe3\x81\x86\xe3\x81\x88\xe3\x81\x8a\n"
    )
    actual = source_to_unicode(source)
    expected = source.decode('utf-8')
    assert actual == expected


def test_utf8_bom():
    unicode_bom = BOM_UTF8.decode('utf-8')

    module = parso.parse(unicode_bom)
    endmarker = module.children[0]
    assert endmarker.type == 'endmarker'
    assert unicode_bom == endmarker.prefix

    module = parso.parse(unicode_bom + 'foo = 1')
    expr_stmt = module.children[0]
    assert expr_stmt.type == 'expr_stmt'
    assert unicode_bom == expr_stmt.get_first_leaf().prefix
