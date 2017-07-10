"""
Testing if parso finds syntax errors and indentation errors.
"""

import pytest

import parso
from parso.python.normalizer import ErrorFinderConfig

def _get_error_list(code, version=None):
    grammar = parso.load_grammar(version)
    tree = grammar.parse(code)
    config = ErrorFinderConfig()
    return list(tree._get_normalizer_issues(config))


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
    errors = [(error.start_pos, error.code) for error in _get_error_list(code)]
    assert [(pos, 901) for pos in positions] == errors


def test_indentation_errors():
    pass
