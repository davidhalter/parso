"""
To ensure compatibility from Python ``2.7`` - ``3.3``, a module has been
created. Clearly there is huge need to use conforming syntax.
"""
import sys
import platform

# unicode function
try:
    unicode = unicode
except NameError:
    unicode = str

is_pypy = platform.python_implementation() == 'PyPy'


try:
    encoding = sys.stdout.encoding
    if encoding is None:
        encoding = 'utf-8'
except AttributeError:
    encoding = 'ascii'


def u(string):
    """Cast to unicode DAMMIT!
    Written because Python2 repr always implicitly casts to a string, so we
    have to cast back to a unicode (and we know that we always deal with valid
    unicode, because we check that in the beginning).
    """
    if sys.version_info.major >= 3:
        return str(string)

    if not isinstance(string, unicode):
        return unicode(str(string), 'UTF-8')
    return string
