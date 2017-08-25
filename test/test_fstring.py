import pytest

from parso import load_grammar, ParserSyntaxError


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
        '{1::>4}',
        '{foo} {bar}',

        # Invalid, but will be checked, later.
        '{}',
        '{1:}',
        '{:}',
        '{:1}',
        '{!:}',
        '{!}',
        '{!a}',
        '{1:{}}',
        '{1:{:}}',
    ]
)
def test_valid(code, grammar):
    fstring = grammar.parse(code, error_recovery=False)
    assert fstring.type == 'fstring'
    assert fstring.get_code() == code


@pytest.mark.parametrize(
    'code', [
        '}',
        '{',
        '{1!{a}}',
        '{!{a}}',
    ]
)
def test_invalid(code, grammar):
    with pytest.raises(ParserSyntaxError):
        grammar.parse(code, error_recovery=False)

    # It should work with error recovery.
    grammar.parse(code, error_recovery=True)
