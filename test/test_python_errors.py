"""
Testing if parso finds syntax errors and indentation errors.
"""
import sys
from textwrap import dedent

import pytest

import parso
from parso.python.normalizer import ErrorFinderConfig


FAILING_EXAMPLES = [
    '1 +',
    '?',
    # Python/compile.c
    dedent('''\
        for a in [1]:
            try:
                pass
            finally:
                continue
        '''), # 'continue' not supported inside 'finally' clause"
    'continue',
    'break',
    'return',
    'yield',

    # SyntaxError from Python/ast.c
    'f(x for x in bar, 1)',
    'from foo import a,',
    'from __future__ import whatever',
    'from __future__ import braces',
    'from .__future__ import whatever',
    'def f(x=3, y): pass',
    'lambda x=3, y: x',
    '__debug__ = 1',
    'with x() as __debug__: pass',
    # Mostly 3.6 relevant
    '[]: int',
    '[a, b]: int',
    '(): int',
    '(()): int',
    '((())): int',
    '{}: int',
    'True: int',
    '(a, b): int',
    '*star,: int',
    'a, b: int = 3',
    'foo(+a=3)',
    'f(lambda: 1=1)',
    'f(x=1, x=2)',
    'f(**x, y)',
    'f(x=2, y)',
    'f(**x, *y)',
    'f(**x, y=3, z)',
    'a, b += 3',
    '(a, b) += 3',
    '[a, b] += 3',
    '[a, 1] += 3',
    # All assignment tests
    'lambda a: 1 = 1',
    '[x for x in y] = 1',
    '{x for x in y} = 1',
    '{x:x for x in y} = 1',
    '(x for x in y) = 1',
    'None = 1',
    '... = 1',
    'a == b = 1',
    '{a, b} = 1',
    '{a: b} = 1',
    '1 = 1',
    '"" = 1',
    'b"" = 1',
    'b"" = 1',
    '"" "" = 1',
    '1 | 1 = 3',
    '1**1 = 3',
    '~ 1 = 3',
    'not 1 = 3',
    '1 and 1 = 3',
    'def foo(): (yield 1) = 3',
    'def foo(): x = yield 1 = 3',
    'async def foo(): await x = 3',
    '(a if a else a) = a',
    '(True,) = x',
    '([False], a) = x',
    'a, 1 = x',
    'foo() = 1',
    # Cases without the equals but other assignments.
    'with x as foo(): pass',
    'del None',
    'del bar, 1',
    'for x, 1 in []: pass',
    'for (not 1) in []: pass',
    '[x for 1 in y]',
    '[x for a, 3 in y]',
    '(x for 1 in y)',
    '{x for 1 in y}',
    '{x:x for 1 in y}',

    # SyntaxErrors from Python/symtable.c
    'def f(x, x): pass',
    'def x(): from math import *',
    'nonlocal a',
    dedent('''
        def glob():
            x = 3
            x.z
            global x'''),
    dedent('''
        def glob():
            x = 3
            global x'''),
    dedent('''
        def glob():
            x
            global x'''),
    dedent('''
        def glob():
            x = 3
            x.z
            nonlocal x'''),
    dedent('''
        def glob():
            x = 3
            nonlocal x'''),
    dedent('''
        def glob():
            x
            nonlocal x'''),
    # Annotation issues
    dedent('''
        def glob():
            x[0]: foo
            global x'''),
    dedent('''
        def glob():
            x.a: foo
            global x'''),
    dedent('''
        def glob():
            x: foo
            global x'''),
    dedent('''
        def glob():
            x: foo = 5
            global x'''),
    dedent('''
        def glob():
            x: foo = 5
            x
            global x'''),
    dedent('''
        def glob():
            global x
            x: foo = 3
        '''),
    # global/nonlocal + param
    dedent('''
        def glob(x):
            global x
        '''),
    dedent('''
        def glob(x):
            nonlocal x
        '''),
    dedent('''
        def x():
            a =3
            def z():
                nonlocal a
                a = 3
                nonlocal a
        '''),
    dedent('''
        def x():
            global a
            nonlocal a
        '''),
    # Missing binding of nonlocal



    # IndentationError
    ' foo',
    'def x():\n    1\n 2',
    'def x():\n 1\n  2',
    'if 1:\nfoo',
]

def _get_error_list(code, version=None):
    tree = parso.parse(code, version=version)
    config = ErrorFinderConfig()
    return list(tree._get_normalizer_issues(config))


def assert_comparison(code, error_code, positions):
    errors = [(error.start_pos, error.code) for error in _get_error_list(code)]
    assert [(pos, error_code) for pos in positions] == errors


@pytest.mark.parametrize(
    ('code', 'positions'), [
        ('1 +', [(1, 3)]),
        ('1 +\n', [(1, 3)]),
        ('1 +\n2 +', [(1, 3), (2, 3)]),
        ('x + 2', []),
        ('[\n', [(2, 0)]),
        ('[\ndef x(): pass', [(2, 0)]),
        ('[\nif 1: pass', [(2, 0)]),
        ('1+?', [(1, 2)]),
        ('?', [(1, 0)]),
        ('??', [(1, 0)]),
        ('? ?', [(1, 0)]),
        ('?\n?', [(1, 0), (2, 0)]),
        ('? * ?', [(1, 0)]),
        ('1 + * * 2', [(1, 4)]),
        ('?\n1\n?', [(1, 0), (3, 0)]),
    ]
)
def test_syntax_errors(code, positions):
    assert_comparison(code, 901, positions)


@pytest.mark.parametrize(
    ('code', 'positions'), [
        (' 1', [(1, 0)]),
        ('def x():\n    1\n 2', [(3, 0)]),
        ('def x():\n 1\n  2', [(3, 0)]),
        ('def x():\n1', [(2, 0)]),
    ]
)
def test_indentation_errors(code, positions):
    assert_comparison(code, 903, positions)


@pytest.mark.parametrize('code', FAILING_EXAMPLES)
def test_python_exception_matches(code):
    wanted, line_nr = _get_actual_exception(code)

    errors = _get_error_list(code)
    actual = None
    if errors:
        error, = errors
        actual = error.message
    assert wanted == actual
    assert line_nr == error.start_pos[0]


def _get_actual_exception(code):
    try:
        compile(code, '<unknown>', 'exec')
    except (SyntaxError, IndentationError) as e:
        wanted = e.__class__.__name__ + ': ' + e.msg
        line_nr = e.lineno
    else:
        assert False, "The piece of code should raise an exception."

    # SyntaxError
    # Python 2.6 has a bit different error messages here, so skip it.
    if sys.version_info[:2] == (2, 6) and wanted == 'SyntaxError: unexpected EOF while parsing':
        wanted = 'SyntaxError: invalid syntax'
    return wanted, line_nr


def test_default_except_error_postition():
    # For this error the position seemed to be one line off, but that doesn't
    # really matter.
    code = 'try: pass\nexcept: pass\nexcept X: pass'
    wanted, line_nr = _get_actual_exception(code)
    error, = _get_error_list(code)
    assert wanted == error.message
    assert line_nr != error.start_pos[0]
    # I think this is the better position.
    assert error.start_pos[0] == 2


@pytest.mark.parametrize(
    ('code', 'version'), [
        # SyntaxError
        ('async def bla():\n def x():  await bla()', '3.5'),
        ('yield from []', '3.5'),
        ('async def foo(): yield from []', '3.5'),
        ('async def foo():\n yield x\n return 1', '3.6'),
        ('async def foo():\n yield x\n return 1', '3.6'),
        ('*a, *b = 3, 3', '3.3'),
        ('*a = 3', '3.5'),
        ('del *a, b', '3.5'),
        ('def x(*): pass', '3.5'),
        ('async def foo():\n def nofoo():[x async for x in []]', '3.6'),
        ('[*[] for a in [1]]', '3.5'),
        ('{**{} for a in [1]}', '3.5'),
        ('"s" b""', '3.5'),
        ('b"ä"', '3.5'),
        ('(%s *d) = x' % ('a,' * 256), '3.6')
    ]
)
def test_python_exception_matches_version(code, version):
    if '.'.join(str(v) for v in sys.version_info[:2]) != version:
        pytest.skip()

    wanted, line_nr = _get_actual_exception(code)
    error, = _get_error_list(code)
    assert wanted == error.message


def test_statically_nested_blocks():
    def indent(code):
        lines = code.splitlines(True)
        return ''.join([' ' + line for line in lines])

    def build(code, depth):
        if depth == 0:
            return code

        new_code = 'if 1:\n' + indent(code)
        return build(new_code, depth - 1)

    def get_error(depth, add_func=False):
        code = build('foo', depth)
        if add_func:
            code = 'def bar():\n' + indent(code)
        errors = _get_error_list(code)
        if errors:
            assert errors[0].message == 'SyntaxError: too many statically nested blocks'
            return errors[0]
        return None

    assert get_error(19) is None
    assert get_error(19, add_func=True) is None

    assert get_error(20)
    assert get_error(20, add_func=True)


def test_future_import_first():
    def is_issue(code, *args):
        code = code % args
        return bool(_get_error_list(code))

    i1 = 'from __future__ import division'
    i2 = 'from __future__ import absolute_import'
    assert not is_issue(i1)
    assert not is_issue(i1 + ';' + i2)
    assert not is_issue(i1 + '\n' + i2)
    assert not is_issue('"";' + i1)
    assert not is_issue('"";' + i1)
    assert not is_issue('""\n' + i1)
    assert not is_issue('""\n%s\n%s', i1, i2)
    assert not is_issue('""\n%s;%s', i1, i2)
    assert not is_issue('"";%s;%s ', i1, i2)
    assert not is_issue('"";%s\n%s ', i1, i2)
    assert is_issue('1;' + i1)
    assert is_issue('1\n' + i1)
    assert is_issue('"";1\n' + i1)
    assert is_issue('""\n%s\nfrom x import a\n%s', i1, i2)
    assert is_issue('%s\n""\n%s', i1, i2)


def test_named_argument_issues(works_not_in_py):
    message = works_not_in_py.get_error_message('def foo(*, **dict): pass')
    message = works_not_in_py.get_error_message('def foo(*): pass')
    if works_not_in_py.version.startswith('2'):
        assert message == 'SyntaxError: invalid syntax'
    else:
        assert message == 'SyntaxError: named arguments must follow bare *'

    works_not_in_py.assert_no_error_in_passing('def foo(*, name): pass')
    works_not_in_py.assert_no_error_in_passing('def foo(bar, *, name=1): pass')
    works_not_in_py.assert_no_error_in_passing('def foo(bar, *, name=1, **dct): pass')
