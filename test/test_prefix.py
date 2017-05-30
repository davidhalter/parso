import pytest
import parso


@pytest.mark.parametrize(('string', 'tokens'), [
    ('#', ['#']),
    (' # ', [' ', '# ']),
    (' # \n', [' ', '# ', '\n']),
    (' # \f\n', [' ', '# ', '\f', '\n']),
    ('  \n', ['  ', '\n']),
    ('  \n ', ['  ', '\n', ' ']),
    (' \f ', [' ', '\f', ' ']),
    (' \f ', [' ', '\f', ' ']),
    (' \r\n', [' ', '\r\n']),
    ('\\', ['\\']),
    ('\\\n', ['\\\n']),
    ('\\\r\n', ['\\\r\n']),
])
def test_simple_prefix_splitting(string, tokens):
    tree = parso.parse(string)
    leaf = tree.children[0]
    assert leaf.type == 'endmarker'
    parsed_tokens = list(leaf._split_prefix())
    assert [t.value for t in parsed_tokens] == tokens
