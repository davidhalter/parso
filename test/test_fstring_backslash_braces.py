"""A backslash does not escape replacement-field braces in f-strings."""

import ast

import pytest

import parso
from parso.parser import ParserSyntaxError


@pytest.mark.parametrize('prefix', ['rf', 'fr', 'RF', 'FR'])
@pytest.mark.parametrize('quote', ['"', "'", '"""', "'''"])
@pytest.mark.parametrize('slashes', [1, 2, 3])
def test_raw_fstring_backslash_before_field(prefix, quote, slashes):
    code = prefix + quote + '\\' * slashes + '{value:0>3o}' + quote
    ast.parse(code)
    grammar = parso.load_grammar(version='3.13')
    module = grammar.parse(code, error_recovery=False)
    assert module.get_code() == code
    assert not list(grammar.iter_errors(module))
    assert any(leaf.value == 'value' for leaf in module.get_used_names()['value'])


@pytest.mark.parametrize('prefix', ['rf', 'fr'])
@pytest.mark.parametrize('quote', ['"', '"""'])
def test_backslash_cannot_escape_unmatched_closing_brace(prefix, quote):
    code = prefix + quote + '\\}' + quote
    with pytest.raises(SyntaxError):
        ast.parse(code)
    with pytest.raises(ParserSyntaxError):
        parso.parse(code, version='3.13', error_recovery=False)
