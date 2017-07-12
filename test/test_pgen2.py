"""Test suite for 2to3's parser and grammar files.

This is the place to add tests for changes to 2to3's grammar, such as those
merging the grammars for Python 2 and 3. In addition to specific tests for
parts of the grammar we've changed, we also make sure we can parse the
test_grammar.py files from both Python 2 and Python 3.
"""

from textwrap import dedent

import pytest

from parso._compatibility import py_version
from parso import load_grammar
from parso import ParserSyntaxError


def _parse(code, version=None):
    code = dedent(code) + "\n\n"
    grammar = load_grammar(version=version)
    return grammar.parse(code, error_recovery=False)


def test_formfeed():
    s = """print 1\n\x0Cprint 2\n"""
    t = _parse(s, '2.7')
    assert t.children[0].children[0].type == 'print_stmt'
    assert t.children[1].children[0].type == 'print_stmt'
    s = """1\n\x0C\x0C2\n"""
    t = _parse(s, '2.7')


def _invalid_syntax(code, version=None, **kwargs):
    with pytest.raises(ParserSyntaxError):
        module = _parse(code, **kwargs)
        # For debugging
        print(module.children)


@pytest.mark.skipif('sys.version_info[:2] < (3, 5)')
def test_matrix_multiplication_operator():
    _parse("a @ b", "3.5")
    _parse("a @= b", "3.5")


def test_yield_from():
    yfrom = "yield from x"
    _parse(yfrom, '3.3')
    _invalid_syntax(yfrom, '2.7')
    _parse("(yield from x) + y", '3.3')
    _invalid_syntax("yield from", '3.3')


@pytest.mark.skipif('sys.version_info[:2] < (3, 5)')
def test_await_expr():
    _parse("""async def foo():
                         await x
                  """, "3.5")

    _parse("""async def foo():

        def foo(): pass

        def foo(): pass

        await x
    """, "3.5")

    _parse("""async def foo(): return await a""", "3.5")

    _parse("""def foo():
        def foo(): pass
        async def foo(): await x
    """, "3.5")


@pytest.mark.skipif('sys.version_info[:2] < (3, 5)')
@pytest.mark.xfail(reason="acting like python 3.7")
def test_await_expr_invalid():
    _invalid_syntax("await x", version="3.5")
    _invalid_syntax("""def foo():
                               await x""", version="3.5")

    _invalid_syntax("""def foo():
        def foo(): pass
        async def foo(): pass
        await x
    """, version="3.5")


@pytest.mark.skipif('sys.version_info[:2] < (3, 5)')
@pytest.mark.xfail(reason="acting like python 3.7")
def test_async_var():
    _parse("""async = 1""", "3.5")
    _parse("""await = 1""", "3.5")
    _parse("""def async(): pass""", "3.5")


@pytest.mark.skipif('sys.version_info[:2] < (3, 5)')
def test_async_for():
    _parse("""async def foo():
                         async for a in b: pass""", "3.5")


@pytest.mark.skipif('sys.version_info[:2] < (3, 5)')
@pytest.mark.xfail(reason="acting like python 3.7")
def test_async_for_invalid():
    _invalid_syntax("""def foo():
                               async for a in b: pass""", version="3.5")


@pytest.mark.skipif('sys.version_info[:2] < (3, 5)')
def test_async_with():
    _parse("""async def foo():
                         async with a: pass""", "3.5")

    @pytest.mark.skipif('sys.version_info[:2] < (3, 5)')
    @pytest.mark.xfail(reason="acting like python 3.7")
    def test_async_with_invalid():
        _invalid_syntax("""def foo():
                                   async with a: pass""", version="3.5")


def test_raise_3x_style_1(each_version):
    _parse("raise", each_version)


def test_raise_2x_style_2(each_py2_version):
    _parse("raise E, V", version=each_py2_version)

def test_raise_2x_style_3(each_py2_version):
    _parse("raise E, V, T", version=each_py2_version)

def test_raise_2x_style_invalid_1(each_py2_version):
    _invalid_syntax("raise E, V, T, Z", version=each_py2_version)

def test_raise_3x_style():
    _parse("raise E1 from E2", '3.3')

def test_raise_3x_style_invalid_1():
    _invalid_syntax("raise E, V from E1", '3.3')

def test_raise_3x_style_invalid_2():
    _invalid_syntax("raise E from E1, E2", '3.3')

def test_raise_3x_style_invalid_3():
    _invalid_syntax("raise from E1, E2", '3.3')

def test_raise_3x_style_invalid_4():
    _invalid_syntax("raise E from", '3.3')


# Adapted from Python 3's Lib/test/test_grammar.py:GrammarTests.testFuncdef
def test_annotation_1():
    _parse("""def f(x) -> list: pass""")

def test_annotation_2(each_py3_version):
    _parse("""def f(x:int): pass""", each_py3_version)

def test_annotation_3(each_py3_version):
    _parse("""def f(*x:str): pass""", each_py3_version)

def test_annotation_4(each_py3_version):
    _parse("""def f(**x:float): pass""", each_py3_version)

def test_annotation_5(each_py3_version):
    _parse("""def f(x, y:1+2): pass""", each_py3_version)

def test_annotation_6():
    _invalid_syntax("""def f(a, (b:1, c:2, d)): pass""")

def test_annotation_7():
    _invalid_syntax("""def f(a, (b:1, c:2, d), e:3=4, f=5, *g:6): pass""")

def test_annotation_8():
    s = """def f(a, (b:1, c:2, d), e:3=4, f=5,
                    *g:6, h:7, i=8, j:9=10, **k:11) -> 12: pass"""
    _invalid_syntax(s)


def test_except_new():
    s = """
        try:
            x
        except E as N:
            y"""
    _parse(s)

def test_except_old():
    s = """
        try:
            x
        except E, N:
            y"""
    _parse(s, version='2.7')


# Adapted from Python 3's Lib/test/test_grammar.py:GrammarTests.testAtoms
def test_set_literal_1():
    _parse("""x = {'one'}""")

def test_set_literal_2():
    _parse("""x = {'one', 1,}""")

def test_set_literal_3():
    _parse("""x = {'one', 'two', 'three'}""")

def test_set_literal_4():
    _parse("""x = {2, 3, 4,}""")


def test_new_octal_notation():
    code = """0o7777777777777"""
    if py_version >= 30:
        _parse(code)
    else:
        _invalid_syntax(code)
    _invalid_syntax("""0o7324528887""")

def test_new_binary_notation():
    _parse("""0b101010""")
    _invalid_syntax("""0b0101021""")


def test_class_new_syntax():
    _parse("class B(t=7): pass")
    _parse("class B(t, *args): pass")
    _parse("class B(t, **kwargs): pass")
    _parse("class B(t, *args, **kwargs): pass")
    _parse("class B(t, y=9, *args, **kwargs): pass")


def test_parser_idempotency_extended_unpacking():
    """A cut-down version of pytree_idempotency.py."""
    _parse("a, *b, c = x\n")
    _parse("[*a, b] = x\n")
    _parse("(z, *y, w) = m\n")
    _parse("for *z, m in d: pass\n")


@pytest.mark.skipif('sys.version_info[0] < 3')
def test_multiline_bytes_literals():
    """
    It's not possible to get the same result when using \xaa in Python 2/3,
    because it's treated differently.
    """
    s = """
        md5test(b"\xaa" * 80,
                (b"Test Using Larger Than Block-Size Key "
                 b"and Larger Than One Block-Size Data"),
                "6f630fad67cda0ee1fb1f562db3aa53e")
        """
    _parse(s)

def test_multiline_bytes_tripquote_literals():
    s = '''
        b"""
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN">
        """
        '''
    _parse(s)

@pytest.mark.skipif('sys.version_info[0] < 3')
def test_multiline_str_literals():
    s = """
        md5test("\xaa" * 80,
                ("Test Using Larger Than Block-Size Key "
                 "and Larger Than One Block-Size Data"),
                "6f630fad67cda0ee1fb1f562db3aa53e")
        """
    _parse(s)
