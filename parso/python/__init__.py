"""
Parsers for Python
"""

def parse(code, **kwargs):
    from parso import load_python_grammar
    grammar = load_python_grammar()
    return grammar.parse(code, **kwargs)
