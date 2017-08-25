import pytest

from parso import load_grammar, ParserSyntaxError
from parso.python.fstring import tokenize


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

        # Escapes
        '{{}}',
        '{{{1}}}',
        '{{{1}',
        '1{{2{{3',
        '}}',
        '{:}}}',

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
    #grammar.parse(code, error_recovery=True)


@pytest.mark.parametrize(
    ('code', 'start_pos', 'positions'), [
        # 2 times 2, 5 because python expr and endmarker.
        ('}{', (2, 3), [(2, 3), (2, 4), (2, 5), (2, 5)]),
        (' :{ 1 : } ', (1, 0), [(1, 2), (1, 3), (1, 6), (1, 8), (1, 10)]),
        ('\n{\nfoo\n }', (2, 1), [(3, 0), (3, 1), (5, 1), (5, 2)]),
    ]
)
def test_tokenize_start_pos(code, start_pos, positions):
    tokens = tokenize(code, start_pos)
    assert positions == [p.start_pos for p in tokens]
