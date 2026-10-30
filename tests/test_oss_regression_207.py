import pytest

from parso import load_grammar
from parso.python.token import PythonTokenTypes
from parso.python.tokenize import tokenize


@pytest.mark.parametrize('prefix', ['f', 'rf', 'fr', 'RF'])
@pytest.mark.parametrize('quote', ['"', "'", '"""', "'''"])
@pytest.mark.parametrize('expression', ['value:>3o', 'ord_(c):0>3o'])
def test_backslash_before_fstring_replacement_field(prefix, quote, expression):
    code = prefix + quote + '\\{' + expression + '}' + quote
    tokens = list(tokenize(code, version_info=(3, 10)))

    assert (tokens[1].type, tokens[1].string) == (
        PythonTokenTypes.FSTRING_STRING, '\\'
    ), 'A backslash must not consume the opening replacement-field brace'
    assert (tokens[2].type, tokens[2].string) == (PythonTokenTypes.OP, '{')

    module = load_grammar(version='3.10').parse(code, error_recovery=False)
    assert module.get_code() == code
    assert module.children[0].children[2].type == 'fstring_expr'
