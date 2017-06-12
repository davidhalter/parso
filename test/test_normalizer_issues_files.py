"""
To easily verify if our normalizer raises the right error codes, just use the
tests of pydocstyle.
"""

import re
from textwrap import dedent

import parso


def collect_errors(code):
    for line_nr, line in enumerate(code.splitlines(), 1):
        match = re.match(r'(\s*)#: (.*)$', line)
        if match is not None:
            codes = match.group(2)
            for code in codes.split():
                code, _, add_indent = code.partition(':')
                column = int(add_indent or len(match.group(1)))

                code, _, add_line = code.partition('+')
                l = line_nr + 1 + int(add_line or 0)

                yield "%s@(%s,%s)" % (code[1:], l, column)


def test_normalizer_issue(normalizer_issue_file):
    with open(normalizer_issue_file.path) as f:
        code = f.read()

    desired = list(collect_errors(code))

    module = parso.parse(code)
    issues = module._get_normalizer_issues()

    i = set("%s@(%s,%s)" % (i.code, i.start_pos[0], i.start_pos[1]) for i in issues)
    d = set(desired)
    assert i == d, dedent("""
        Test %r failed (%s of %s passed).
        not raised  = %s
        unexpected = %s
        """) % (
            normalizer_issue_file.name, len(i & d), len(d),
            sorted(d - i), sorted(i - d)
        )
