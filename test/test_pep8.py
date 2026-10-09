import parso
import pytest


def issues(code):
    grammar = parso.load_grammar()
    module = parso.parse(code)
    return grammar._get_normalizer_issues(module)


def test_eof_newline():
    def assert_issue(code):
        found = issues(code)
        assert len(found) == 1
        issue, = found
        assert issue.code == 292

    assert not issues('asdf = 1\n')
    assert not issues('asdf = 1\r\n')
    assert not issues('asdf = 1\r')
    assert_issue('asdf = 1')
    assert_issue('asdf = 1\n# foo')
    assert_issue('# foobar')
    assert_issue('')
    assert_issue('foo = 1  # comment')


def test_eof_blankline():
    def assert_issue(code):
        found = issues(code)
        assert len(found) == 1
        issue, = found
        assert issue.code == 391

    assert_issue('asdf = 1\n\n')
    assert_issue('# foobar\n\n')
    assert_issue('\n\n')


def test_shebang():
    assert not issues('#!\n')
    assert not issues('#!/foo\n')
    assert not issues('#! python\n')


@pytest.mark.parametrize('newline', ['\n', '\r\n', '\r'])
@pytest.mark.parametrize('backslashes', [1, 2])
@pytest.mark.parametrize('comment', ['#', '# comment'])
def test_comment_after_backslash(newline, backslashes, comment):
    prefix = ('\\' + newline) * backslashes
    found = issues(prefix + comment)
    assert [(issue.code, issue.start_pos) for issue in found] == [
        (292, (backslashes + 1, len(comment))),
    ]
