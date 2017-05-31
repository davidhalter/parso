import re

from parso.tokenize import group


class PrefixPart(object):
    def __init__(self, typ, value, start_pos):
        self.type = typ
        self.value = value
        self.start_pos = start_pos

    @property
    def end_pos(self):
        if self.value.endswith('\n'):
            return self.start_pos[0] + 1, 0
        return self.start_pos[0], self.start_pos[1] + len(self.value)


_comment = r'#[^\n\r\f]*'
_backslash = r'\\\r?\n?'
_whitespace = r' +'
_tabs = r'\t+'
_newline = r'\r?\n'
_form_feed = r'\f'

_regex = group(_comment, _backslash, _whitespace, _newline, _form_feed, _tabs)
_regex = re.compile(_regex)


_types = {
    ' ': 'spaces',
    '#': 'comment',
    '\\': 'backslash',
    '\f': 'formfeed',
    '\n': 'newline',
    '\r': 'newline',
    '\t': 'tabs',
}


def split_prefix(prefix, start_pos):
    line, column = start_pos
    start = 0
    while start != len(prefix):
        match =_regex.match(prefix, start)
        value = match.group(0)
        typ = _types[value[0]]
        yield PrefixPart(typ, value, (line, column + start))

        start = match.end(0)
        if value.endswith('\n'):
            line += 1
            column = -start
