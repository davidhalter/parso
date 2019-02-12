import pytest
from textwrap import dedent

from parso import load_grammar, ParserSyntaxError
from parso.python.tokenize import tokenize


@pytest.fixture
def grammar():
    return load_grammar(version='3.6')


@pytest.mark.parametrize(
    'code', [
        '{1}',
        '{1:}',
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
    ]
)
def test_valid(code, grammar):
    code = 'f"""%s"""' % code
    module = grammar.parse(code, error_recovery=False)
    fstring = module.children[0]
    assert fstring.type == 'fstring'
    assert fstring.get_code() == code


@pytest.mark.parametrize(
    'code', [
        '}',
        '{',
        '{1!{a}}',
        '{!{a}}',
        '{}',
        '{:}',
        '{:}}}',
        '{:1}',
        '{!:}',
        '{!}',
        '{!a}',
        '{1:{}}',
        '{1:{:}}',
    ]
)
def test_invalid(code, grammar):
    code = 'f"""%s"""' % code
    with pytest.raises(ParserSyntaxError):
        grammar.parse(code, error_recovery=False)

    # It should work with error recovery.
    grammar.parse(code, error_recovery=True)


@pytest.mark.parametrize(
    ('code', 'positions'), [
        # 2 times 2, 5 because python expr and endmarker.
        ('f"}{"', [(1, 0), (1, 2), (1, 3), (1, 4), (1, 5)]),
        ('f" :{ 1 : } "', [(1, 0), (1, 2), (1, 4), (1, 6), (1, 8), (1, 9),
                           (1, 10), (1, 11), (1, 12), (1, 13)]),
        ('f"""\n {\nfoo\n }"""', [(1, 0), (1, 4), (2, 1), (3, 0), (4, 1),
                                  (4, 2), (4, 5)]),
    ]
)
def test_tokenize_start_pos(code, positions):
    tokens = list(tokenize(code, version_info=(3, 6)))
    assert positions == [p.start_pos for p in tokens]


@pytest.mark.parametrize(
    'code', [
        dedent("""\
            f'''s{
               str.uppe
            '''
            """),
        'f"foo',
        'f"""foo',
    ]
)
def test_roundtrip(grammar, code):
    tree = grammar.parse(code)
    assert tree.get_code() == code
