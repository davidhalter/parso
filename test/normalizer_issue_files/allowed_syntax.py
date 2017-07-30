"""
Some syntax errors are a bit complicated and need exact checking. Here we
gather some of the potentially dangerous ones.
"""

from __future__ import division

# With a dot it's not a future import anymore.
from .__future__ import absolute_import

'' ''
''r''u''
b'' BR''

foo: int = 4
(foo): int = 3
((foo)): int = 3
foo.bar: int
foo[3]: int

for x in [1]:
    try:
        continue  # Only the other continue and pass is an error.
    finally:
        #: E901
        continue


for x in [1]:
    break
    continue

try:
    pass
except ZeroDivisionError:
    pass
    #: E722:0
except:
    pass

try:
    pass
    #: E722:0 E901:0
except:
    pass
except ZeroDivisionError:
    pass


class X():
    nonlocal a


def c():
    class X():
        nonlocal a


def x():
    a = 3

    def y():
        nonlocal a


def x():
    def y():
        nonlocal a

    a = 3


def x():
    a = 3

    def y():
        class z():
            nonlocal a


a = *args, *args
error[(*args, *args)] = 3
*args, *args


def glob():
    global x
    y: foo = x
