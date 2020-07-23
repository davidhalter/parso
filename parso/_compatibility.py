"""
To ensure compatibility from Python ``2.7`` - ``3.3``, a module has been
created. Clearly there is huge need to use conforming syntax.
"""
import platform

# unicode function
try:
    unicode = unicode
except NameError:
    unicode = str

is_pypy = platform.python_implementation() == 'PyPy'
