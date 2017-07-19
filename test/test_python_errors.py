"""
Testing if parso finds syntax errors and indentation errors.
"""

import pytest
from textwrap import dedent

import parso
from parso.python.normalizer import ErrorFinderConfig

def _get_error_list(code, version=None):
    grammar = parso.load_grammar(version=version)
    tree = grammar.parse(code)
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


@pytest.mark.parametrize(
    'code', [
        # SyntaxError
        '1 +',
        '?',
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
        'try: pass\nexcept: pass\nexcept X: pass',

        # IndentationError
        ' foo',
        'def x():\n    1\n 2',
        'def x():\n 1\n  2',
        'if 1:\nfoo',
    ]
)
def test_python_exception_matches(code):
    error, = _get_error_list(code)
    try:
        compile(code, '<unknown>', 'exec')
    except (SyntaxError, IndentationError) as e:
        wanted = e.__class__.__name__ + ': ' + e.msg
    else:
        assert False, "The piece of code should raise an exception."
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
