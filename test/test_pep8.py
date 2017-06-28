import parso


def issues(code):
    module = parso.parse(code)
    return module._get_normalizer_issues()


def test_eof_newline():
    def assert_issue(code):
        found = issues(code)
        assert len(found) == 1
        issue, = found
        assert issue.code == 292

    assert not issues('asdf = 1\n')
    assert_issue('asdf = 1')
    assert_issue('asdf = 1\n#')
    assert_issue('# foobar')
    assert_issue('')
    assert_issue('foo = 1  # comment')
