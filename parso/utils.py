from collections import namedtuple
import re
from ast import literal_eval

from parso._compatibility import unicode


def splitlines(string, keepends=False):
    """
    A splitlines for Python code. In contrast to Python's ``str.splitlines``,
    looks at form feeds and other special characters as normal text. Just
    splits ``\n`` and ``\r\n``.
    Also different: Returns ``['']`` for an empty string input.

    In Python 2.7 form feeds are used as normal characters when using
    str.splitlines. However in Python 3 somewhere there was a decision to split
    also on form feeds.
    """
    if keepends:
        lst = string.splitlines(True)

        # We have to merge lines that were broken by form feed characters.
        merge = []
        for i, line in enumerate(lst):
            if line.endswith('\f'):
                merge.append(i)

        for index in reversed(merge):
            try:
                lst[index] = lst[index] + lst[index + 1]
                del lst[index + 1]
            except IndexError:
                # index + 1 can be empty and therefore there's no need to
                # merge.
                pass

        # The stdlib's implementation of the end is inconsistent when calling
        # it with/without keepends. One time there's an empty string in the
        # end, one time there's none.
        if string.endswith('\n') or string == '':
            lst.append('')
        return lst
    else:
        return re.split('\n|\r\n', string)


def source_to_unicode(source, encoding=None):
    def detect_encoding():
        """
        For the implementation of encoding definitions in Python, look at:
        - http://www.python.org/dev/peps/pep-0263/
        - http://docs.python.org/2/reference/lexical_analysis.html#encoding-declarations
        """
        byte_mark = literal_eval(r"b'\xef\xbb\xbf'")
        if source.startswith(byte_mark):
            # UTF-8 byte-order mark
            return 'utf-8'

        first_two_lines = re.match(br'(?:[^\n]*\n){0,2}', source).group(0)
        possible_encoding = re.search(br"coding[=:]\s*([-\w.]+)",
                                      first_two_lines)
        if possible_encoding:
            return possible_encoding.group(1)
        else:
            # the default if nothing else has been set -> PEP 263
            return encoding if encoding is not None else 'utf-8'

    if isinstance(source, unicode):
        # only cast str/bytes
        return source

    encoding = detect_encoding()
    if not isinstance(encoding, unicode):
        encoding = unicode(encoding, 'utf-8', 'replace')
    # cast to unicode by default
    return unicode(source, encoding, 'replace')


def version_info():
    """
    Returns a namedtuple of parso's version, similar to Python's
    ``sys.version_info``.
    """
    Version = namedtuple('Version', 'major, minor, micro')
    from parso import __version__
    tupl = re.findall('[a-z]+|\d+', __version__)
    return Version(*[x if i == 3 else int(x) for i, x in enumerate(tupl)])
