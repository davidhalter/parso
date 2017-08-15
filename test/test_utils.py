from codecs import BOM_UTF8

from parso.utils import split_lines, python_bytes_to_unicode
import parso


def test_split_lines_no_keepends():
    assert split_lines('asd\r\n') == ['asd', '']
    assert split_lines('asd\r\n\f') == ['asd', '\f']
    assert split_lines('\fasd\r\n') == ['\fasd', '']
    assert split_lines('') == ['']
    assert split_lines('\n') == ['', '']


def test_split_lines_keepends():
    assert split_lines('asd\r\n', keepends=True) == ['asd\r\n', '']
    assert split_lines('asd\r\n\f', keepends=True) == ['asd\r\n', '\f']
    assert split_lines('\fasd\r\n', keepends=True) == ['\fasd\r\n', '']
    assert split_lines('', keepends=True) == ['']
    assert split_lines('\n', keepends=True) == ['\n', '']


def test_python_bytes_to_unicode_unicode_text():
    source = (
        b"# vim: fileencoding=utf-8\n"
        b"# \xe3\x81\x82\xe3\x81\x84\xe3\x81\x86\xe3\x81\x88\xe3\x81\x8a\n"
    )
    actual = python_bytes_to_unicode(source)
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
