import re

from parso.tokenize import group


class PrefixToken(object):
    def __init__(self, typ, value, start_pos):
        self.type = typ
        self.value = value
        self.start_pos = start_pos

    @property
    def end_pos(self):
        if '\n' in self.value:
            return self.start_pos[0] + 1, 0
        return self.end_pos[1]


_comment = r'#[^\n\r\f]*'
_backslash = r'\\\r?\n?'
_whitespace = r' +'
_newline = r'\r?\n'
_form_feed = r'\f'

_regex = group(_comment, _backslash, _whitespace, _newline, _form_feed)
_regex = re.compile(_regex)


_types = {
    ' ': 'spaces',
    '#': 'comment',
    '\\': 'backslash',
    '\f': 'formfeed',
    '\n': 'newline',
    '\r': 'newline'
}


def split_prefix(prefix, start_pos):
    line, column = start_pos
    start = 0
    while start != len(prefix):
        match =_regex.match(prefix, start)
        value = match.group(0)
        typ = _types[value[0]]
        yield PrefixToken(typ, value, (line, column + start))

        start = match.end(0)
        if '\n' in value:
            line += 1
            column = -start
