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
    start_pos = (1, 0)
    for pt, expected in zip(parsed_tokens, tokens):
        assert pt.value == expected

        # Calculate the estimated end_pos
        if expected.endswith('\n'):
            end_pos = start_pos[0] + 1, 0
        else:
            end_pos = start_pos[0], start_pos[1] + len(expected)

        #assert start_pos == pt.start_pos
        assert end_pos == pt.end_pos
        start_pos = end_pos


@pytest.mark.parametrize(('string', 'types'), [
    ('# ', ['comment']),
    ('\r\n', ['newline']),
    ('\f', ['formfeed']),
    ('\\\n', ['backslash']),
])
def test_prefix_splitting_types(string, types):
    tree = parso.parse(string)
    leaf = tree.children[0]
    assert leaf.type == 'endmarker'
    parsed_tokens = list(leaf._split_prefix())
    assert [t.type for t in parsed_tokens] == types
