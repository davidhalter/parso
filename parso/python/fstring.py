import re

from parso.utils import PythonVersionInfo
from parso.python.tokenize import Token
from parso.python import token

version36 = PythonVersionInfo(3, 6)


class TokenNamespace:
    LBRACE = token.LBRACE,
    RBRACE = token.RBRACE
    ENDMARKER = token.ENDMARKER
    ERRORTOKEN = token.ERRORTOKEN
    COLON = token.COLON
    CONVERSION = 100
    PYTHON_EXPR = 101
    EXCLAMATION_MARK = 102

    @classmethod
    def generate_token_id(cls, string):
        if string == '{':
            return cls.LBRACE
        elif string == '}':
            return cls.RBRACE
        elif string == '!':
            return cls.EXCLAMATION_MARK
        return getattr(cls, string)


GRAMMAR = """
fstring: expressions ENDMARKER
expressions: expression*
expression: '{' PYTHON_EXPR [ '!' CONVERSION ] [ ':' expressions ] '}'
"""

_prefix = r'((?:[^{}]+|\}\}|\{\{)*)'
_expr = _prefix + r'(\{|\}|$)'
_in_expr = r'[^{}\[\]:"\'!]*(.?)'
# There's only one conversion character allowed. But the rules have to be
# checked later anyway, so allow more here. This makes error recovery nicer.
_conversion = r'([^={}:]+)(.?)'

_compiled_expr = re.compile(_expr)
_compiled_in_expr = re.compile(_in_expr)
_compiled_conversion = re.compile(_conversion)


def tokenize(code, start_pos=(1, 0)):
    def tok(value, type=None, prefix=''):
        if type is None:
            type = TokenNamespace.generate_token_id(found)
        return Token(type, value, (line, column), prefix)

    code = ''
    start = 0
    while True:
        match = _compiled_expr.match(code, start)
        prefix = match.group(1)
        found = match.group(2)
        start = match.end()
        if not found:
            # We're at the end.
            break

        if found == '}':
            yield tok(found, prefix=prefix)
        else:
            assert found == '{'
            yield tok(found, prefix=prefix)

            expression = ''
            squared_count = 0
            curly_count = 0
            while True:
                expr_match = _compiled_in_expr.match(code, start)
                expression += expr_match.group(0)
                found = expr_match.group(2)
                start = expr_match.end()

                if found == '{':
                    curly_count += 1
                    expression += found
                elif found == '}' and curly_count > 0:
                    curly_count -= 1
                    expression += found
                elif found == '[':
                    squared_count += 1
                    expression += found
                elif found == ']':
                    # Use a max function here, because the Python code might
                    # just have syntax errors.
                    squared_count = max(0, squared_count - 1)
                    expression += found
                elif found == ':' and (squared_count or curly_count):
                    expression += found
                elif found in ('"', "'"):
                    expression += found
                    search = found
                    if len(code) > start + 1 and  \
                            code[start] == found == code[start+1]:
                        search *= 3
                        start += 2

                    index = code.find(search)
                    if index == -1:
                        index = len(code)
                    expression += code[start:index]
                    start = index
                elif found == '!' and len(code) > start and code[start] == '=':
                    # This is a python `!=` and not a conversion.
                    expression += found
                else:
                    yield tok(expression, type=TokenNamespace.PYTHON_EXPR)
                    if found:
                        yield tok(found)
                    break

            if found == '!':
                conversion_match = _compiled_conversion.match(code, start)
                found = conversion_match.group(2)
                start = conversion_match.end()
                yield tok(conversion_match.group(1))
                if found:
                    yield tok(found)

            # We don't need to handle everything after ':', because that is
            # basically new tokens.

    yield tok('', type=TokenNamespace.ENDMARKER, prefix=prefix)
