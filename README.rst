###################################################################
parso - A Python Parser Written in Python
###################################################################

.. image:: https://secure.travis-ci.org/davidhalter/parso.png?branch=master
    :target: http://travis-ci.org/davidhalter/parso
    :alt: Travis-CI build status

.. image:: https://coveralls.io/repos/davidhalter/parso/badge.png?branch=master
    :target: https://coveralls.io/r/davidhalter/parso
    :alt: Coverage Status


Parso is a Python parser that supports error recovery and round-trip parsing.

Parso has been battle-tested by jedi_. It was pulled out of jedi to be useful
for other projects as well.

Parso is very simplistic. It consists of a small API to parse Python and
analyse the parsing tree.


Ressources
==========

- `PyPI <https://pypi.python.org/pypi/parso>`_
- `Docs <https://parso.readthedocs.org/en/latest/>`_
- Uses `semantic versioning <http://semver.org/>`_

Installation
============

    pip install parso

Future
======

- There will be better support for refactoring and comments. Stay tuned.
- There's a WIP PEP8 validator. It's however not in a good shape, yet.

Known Issues
============

- `async`/`await` are already used as keywords in Python3.6.
- `from __future__ import print_function` is not supported,

Testing
=======

The test suite depends on ``tox`` and ``pytest``::

    pip install tox pytest

To run the tests for all supported Python versions::

    tox

If you want to test only a specific Python version (e.g. Python 2.7), it's as
easy as ::

    tox -e py27

Tests are also run automatically on `Travis CI
<https://travis-ci.org/davidhalter/parso/>`_.

Acknowledgements
================

- Guido van Rossum (@gvanrossum) for creating the parser generator pgen2
  (originally used in lib2to3).


.. _jedi: https://github.com/davidhalter/jedi
