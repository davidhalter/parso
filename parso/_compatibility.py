"""
To ensure compatibility from Python ``2.6`` - ``3.3``, a module has been
created. Clearly there is huge need to use conforming syntax.
"""
import sys

# Cannot use sys.version.major and minor names, because in Python 2.6 it's not
# a namedtuple.
py_version = int(str(sys.version_info[0]) + str(sys.version_info[1]))

# unicode function
try:
    unicode = unicode
except NameError:
    unicode = str


def use_metaclass(meta, *bases):
    """ Create a class with a metaclass. """
    if not bases:
        bases = (object,)
    return meta("HackClass", bases, {})


try:
    encoding = sys.stdout.encoding
    if encoding is None:
        encoding = 'utf-8'
except AttributeError:
    encoding = 'ascii'


def u(string):
    """Cast to unicode DAMMIT!
    Written because Python2 repr always implicitly casts to a string, so we
    have to cast back to a unicode (and we now that we always deal with valid
    unicode, because we check that in the beginning).
    """
    if py_version >= 30:
        return str(string)

    if not isinstance(string, unicode):
        return unicode(str(string), 'UTF-8')
    return string


try:
    FileNotFoundError = FileNotFoundError
except NameError:
    FileNotFoundError = IOError


def utf8_repr(func):
    """
    ``__repr__`` methods in Python 2 don't allow unicode objects to be
    returned. Therefore cast them to utf-8 bytes in this decorator.
    """
    def wrapper(self):
        result = func(self)
        if isinstance(result, unicode):
            return result.encode('utf-8')
        else:
            return result

    if py_version >= 30:
        return func
    else:
        return wrapper
