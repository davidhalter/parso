import pytest

from parso import load_grammar


@pytest.fixture
def grammar():
    return load_grammar(language="python-f-string")


@pytest.mark.parametrize(
    'code', [
        '{1}',
        '',
        '{1!a}',
        '{1!a:1}',
        '{1:1}',
        '{1:1.{32}}',
    ]
)
def test_valid(code, grammar):
    fstring = grammar.parse(code, error_recovery=False)
    assert fstring.type == 'fstring'
    assert fstring.get_code() == code
