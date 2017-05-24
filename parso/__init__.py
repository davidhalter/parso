"""
parso is a Python parser. It's really easy to use and supports multiple Python
versions, file caching, round-trips and other stuff:

>>> from parso import load_python_grammar
>>> grammar = load_python_grammar(version='2.7')
>>> module = grammar.parse('hello + 1')
>>> stmt = module.children[0]
>>> stmt
PythonNode(simple_stmt, [PythonNode(arith_expr, [...]), <Newline: ''>])
>>> stmt.get_code()
'hello + 1'
>>> name = stmt.children[0].children[0]
>>> name
<Name: hello@1,0>
>>> name.end_pos
(1, 5)
"""

from parso.parser import ParserSyntaxError
from parso.grammar import create_grammar, load_python_grammar


__version__ = '0.0.3'


def parse(code=None, **kwargs):
    """
    A utility function to parse Python with the current Python version. Params
    are documented in ``Grammar.parse``.
    """
    grammar = load_python_grammar()
    return grammar.parse(code, **kwargs)
