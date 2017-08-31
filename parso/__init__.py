"""
parso is a Python parser. It's really easy to use and supports multiple Python
versions, file caching, round-trips and other stuff:

>>> from parso import load_grammar
>>> grammar = load_grammar(version='2.7')
>>> module = grammar.parse('hello + 1')
>>> expr = module.children[0]
>>> expr
PythonNode(arith_expr, [<Name: hello@1,0>, <Operator: +>, <Number: 1>])
>>> print(expr.get_code())
hello + 1
>>> name = expr.children[0]
>>> name
<Name: hello@1,0>
>>> name.end_pos
(1, 5)
>>> expr.end_pos
(1, 9)
"""

from parso.parser import ParserSyntaxError
from parso.grammar import Grammar, load_grammar


__version__ = '0.0.4'


def parse(code=None, **kwargs):
    """
    A utility function to parse Python with the current Python version. Params
    are documented in ``Grammar.parse``.
    """
    version = kwargs.pop('version', None)
    grammar = load_grammar(version=version)
    return grammar.parse(code, **kwargs)
