import re
from codecs import BOM_UTF8

from parso.python.tokenize import group


class PrefixPart(object):
    def __init__(self, leaf, typ, value, spacing='', start_pos=None):
        assert start_pos is not None
        self.parent = leaf
        self.type = typ
        self.value = value
        self.spacing = spacing
        self.start_pos = start_pos

    @property
    def end_pos(self):
        if self.value.endswith('\n'):
            return self.start_pos[0] + 1, 0
        return self.start_pos[0], self.start_pos[1] + len(self.value)

    def create_spacing_part(self):
        column = self.start_pos[1] - len(self.spacing)
        return PrefixPart(
            self.parent, 'spacing', self.spacing,
            start_pos=(self.start_pos[0], column)
        )

    def __repr__(self):
        return '%s(%s, %s, %s)' % (
            self.__class__.__name__,
            self.type,
            repr(self.value),
            self.start_pos
        )


unicode_bom = BOM_UTF8.decode('utf-8')

_comment = r'#[^\n\r\f]*'
_backslash = r'\\\r?\n'
_newline = r'\r?\n'
_form_feed = r'\f'
_only_spacing = '$'
_spacing = r'[ \t]*'
_bom = unicode_bom

_regex = group(
    _comment, _backslash, _newline, _form_feed, _only_spacing, _bom,
    capture=True
)
_regex = re.compile(group(_spacing, capture=True) + _regex)


_types = {
    '#': 'comment',
    '\\': 'backslash',
    '\f': 'formfeed',
    '\n': 'newline',
    '\r': 'newline',
    unicode_bom: 'bom'
}


def split_prefix(leaf, start_pos):
    line, column = start_pos
    start = 0
    value = spacing = ''
    while start != len(leaf.prefix):
        match =_regex.match(leaf.prefix, start)
        spacing = match.group(1)
        value = match.group(2)
        if not value:
            break
        type_ = _types[value[0]]
        yield PrefixPart(
            leaf, type_, value, spacing,
            start_pos=(line, column + start + len(spacing))
        )

        start = match.end(0)
        if value.endswith('\n'):
            line += 1
            column = -start

    if value:
        spacing = ''
    yield PrefixPart(
        leaf, 'spacing', spacing,
        start_pos=(line, column + start)
    )
