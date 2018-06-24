from __future__ import absolute_import

# Map from operator to number (since tokenize doesn't do this)

opmap_raw = """\
( LPAR
) RPAR
[ LSQB
] RSQB
: COLON
, COMMA
; SEMI
+ PLUS
- MINUS
* STAR
/ SLASH
| VBAR
& AMPER
< LESS
> GREATER
= EQUAL
. DOT
% PERCENT
` BACKQUOTE
{ LBRACE
} RBRACE
@ AT
== EQEQUAL
!= NOTEQUAL
<> NOTEQUAL
<= LESSEQUAL
>= GREATEREQUAL
~ TILDE
^ CIRCUMFLEX
<< LEFTSHIFT
>> RIGHTSHIFT
** DOUBLESTAR
+= PLUSEQUAL
-= MINEQUAL
*= STAREQUAL
/= SLASHEQUAL
%= PERCENTEQUAL
&= AMPEREQUAL
|= VBAREQUAL
@= ATEQUAL
^= CIRCUMFLEXEQUAL
<<= LEFTSHIFTEQUAL
>>= RIGHTSHIFTEQUAL
**= DOUBLESTAREQUAL
// DOUBLESLASH
//= DOUBLESLASHEQUAL
-> RARROW
... ELLIPSIS
! EXCLAMATION
"""

opmap = {}
for line in opmap_raw.splitlines():
    op, name = line.split()
    opmap[op] = name


def generate_token_id(string):
    """
    Uses a token in the grammar (e.g. `'+'` or `'and'`returns the corresponding
    ID for it. The strings are part of the grammar file.
    """
    try:
        return opmap[string]
    except KeyError:
        pass
    return globals()[string]


class TokenType(object):
    def __init__(self, name, contains_syntax=False):
        self.name = name
        self.contains_syntax = contains_syntax

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.name)


class TokenTypes(object):
    """
    Basically an enum, but Python 2 doesn't have enums in the standard library.
    """
    def __init__(self, names, contains_syntax):
        for name in names:
            setattr(self, name, TokenType(name, contains_syntax=name in contains_syntax))


PythonTokenTypes = TokenTypes((
    'STRING', 'NUMBER', 'NAME', 'ERRORTOKEN', 'NEWLINE', 'INDENT', 'DEDENT',
    'ERROR_DEDENT', 'FSTRING_STRING', 'FSTRING_START', 'FSTRING_END', 'OP',
    'ENDMARKER'),
    contains_syntax=('NAME', 'OP'),
)
