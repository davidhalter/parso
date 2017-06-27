import re

from parso.tokenize import group


class PrefixPart(object):
    def __init__(self, leaf, typ, value, start_pos):
        self.parent = leaf
        self.type = typ
        self.value = value
        self.start_pos = start_pos

    @property
    def end_pos(self):
        if self.value.endswith('\n'):
            return self.start_pos[0] + 1, 0
        return self.start_pos[0], self.start_pos[1] + len(self.value)

    def __repr__(self):
        return '%s(%s, %s, %s)' % (
            self.__class__.__name__,
            self.type,
            repr(self.value),
            self.start_pos
        )


_comment = r'#[^\n\r\f]*'
_backslash = r'\\\r?\n'
_indentation = r'[ \t]+'
_newline = r'\r?\n'
_form_feed = r'\f'

_regex = group(_comment, _backslash, _indentation, _newline, _form_feed)
_regex = re.compile(_regex)


_types = {
    ' ': 'indentation',
    '#': 'comment',
    '\\': 'backslash',
    '\f': 'formfeed',
    '\n': 'newline',
    '\r': 'newline',
    '\t': 'indentation',
}


def split_prefix(leaf, start_pos):
    line, column = start_pos
    start = 0
    while start != len(leaf.prefix):
        match =_regex.match(leaf.prefix, start)
        value = match.group(0)
        typ = _types[value[0]]
        yield PrefixPart(leaf, typ, value, (line, column + start))

        start = match.end(0)
        if value.endswith('\n'):
            line += 1
            column = -start
