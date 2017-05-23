import os

from parso._compatibility import FileNotFoundError
from parso.parser import ParserSyntaxError
from parso import grammar
from parso.tokenize import generate_tokens
from parso.parser import BaseParser
from parso.python.parser import Parser as PythonParser


__version__ = '0.0.2'

_loaded_grammars = {}


def create_grammar(text, tokenizer=generate_tokens, parser=BaseParser):
    """
    :param text: A BNF representation of your grammar.
    """
    return grammar.Grammar(text, tokenizer=tokenizer, parser=parser)


def load_python_grammar(version=None):
    """
    Loads a Python grammar. The default version is always the latest.

    If you need support for a specific version, please use e.g.
    `version='3.3'`.
    """
    if version is None:
        version = '3.6'

    if version in ('3.2', '3.3'):
        version = '3.4'
    elif version == '2.6':
        version = '2.7'

    file = 'python/grammar' + version + '.txt'

    global _loaded_grammars
    path = os.path.join(os.path.dirname(__file__), file)
    try:
        return _loaded_grammars[path]
    except KeyError:
        try:
            with open(path) as f:
                bnf_text = f.read()
            grammar = create_grammar(bnf_text, parser=PythonParser)
            return _loaded_grammars.setdefault(path, grammar)
        except FileNotFoundError:
            # Just load the default if the file does not exist.
            return load_python_grammar()
