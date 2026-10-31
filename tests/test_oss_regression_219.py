import parso
import pytest


@pytest.mark.parametrize('newline', ['\n', '\r\n', '\r'])
def test_comment_after_line_continuation(newline):
    code = '\\' + newline + '#'
    grammar = parso.load_grammar()
    module = grammar.parse(code)

    try:
        issues = grammar._get_normalizer_issues(module)
    except AttributeError as error:
        raise AssertionError(
            'A comment after a line continuation must not crash normalization'
        ) from error

    assert [(issue.code, issue.start_pos) for issue in issues] == [
        (292, (2, 1))
    ]
    assert module.get_code() == code
