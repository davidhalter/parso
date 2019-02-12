.. :changelog:

Changelog
---------

0.3.4 (2018-02-13)
+++++++++++++++++++

- Fix an f-string tokenizer error

0.3.3 (2018-02-06)
+++++++++++++++++++

- Fix async errors in the diff parser
- A fix in iter_errors
- This is a very small bugfix release

0.3.2 (2018-01-24)
+++++++++++++++++++

- 20+ bugfixes in the diff parser and 3 in the tokenizer
- A fuzzer for the diff parser, to give confidence that the diff parser is in a
  good shape.
- Some bugfixes for f-string

0.3.1 (2018-07-09)
+++++++++++++++++++

- Bugfixes in the diff parser and keyword-only arguments

0.3.0 (2018-06-30)
+++++++++++++++++++

- Rewrote the pgen2 parser generator.

0.2.1 (2018-05-21)
+++++++++++++++++++

- A bugfix for the diff parser.
- Grammar files can now be loaded from a specific path.

0.2.0 (2018-04-15)
+++++++++++++++++++

- f-strings are now parsed as a part of the normal Python grammar. This makes
  it way easier to deal with them.

0.1.1 (2017-11-05)
+++++++++++++++++++

- Fixed a few bugs in the caching layer
- Added support for Python 3.7

0.1.0 (2017-09-04)
+++++++++++++++++++

- Pulling the library out of Jedi. Some APIs will definitely change.
