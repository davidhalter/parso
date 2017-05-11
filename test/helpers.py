"""
A helper module for testing, improves compatibility for testing (as
``jedi._compatibility``) as well as introducing helper functions.
"""

import sys

if sys.hexversion < 0x02070000:
    import unittest2 as unittest
else:
    import unittest

TestCase = unittest.TestCase
