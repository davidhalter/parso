# Copyright 2004-2005 Elemental Security, Inc. All Rights Reserved.
# Licensed to PSF under a Contributor Agreement.

# Modifications:
# Copyright David Halter and Contributors
# Modifications are dual-licensed: MIT and PSF.
# 99% of the code is different from pgen2, now.

"""
The ``Parser`` tries to convert the available Python code in an easy to read
format, something like an abstract syntax tree. The classes who represent this
tree, are sitting in the :mod:`parso.tree` module.

The Python module ``tokenize`` is a very important part in the ``Parser``,
because it splits the code into different words (tokens).  Sometimes it looks a
bit messy. Sorry for that! You might ask now: "Why didn't you use the ``ast``
module for this? Well, ``ast`` does a very good job understanding proper Python
code, but fails to work as soon as there's a single line of broken code.

There's one important optimization that needs to be known: Statements are not
being parsed completely. ``Statement`` is just a representation of the tokens
within the statement. This lowers memory usage and cpu time and reduces the
complexity of the ``Parser`` (there's another parser sitting inside
``Statement``, which produces ``Array`` and ``Call``).
"""
from parso import tree


class ParserSyntaxError(Exception):
    """
    Contains error information about the parser tree.

    May be raised as an exception.
    """
    def __init__(self, message, error_leaf):
        self.message = message
        self.error_leaf = error_leaf


class InternalParseError(Exception):
    """
    Exception to signal the parser is stuck and error recovery didn't help.
    Basically this shouldn't happen. It's a sign that something is really
    wrong.
    """

    def __init__(self, msg, type_, value, start_pos):
        Exception.__init__(self, "%s: type=%r, value=%r, start_pos=%r" %
                           (msg, type_.name, value, start_pos))
        self.msg = msg
        self.type = type
        self.value = value
        self.start_pos = start_pos


class Stack(list):
    def get_tos_nodes(self):
        tos = self[-1]
        return tos[2][1]

    def get_tos_first_tokens(self, grammar):
        tos = self[-1]
        inv_tokens = dict((v, k) for k, v in grammar.tokens.items())
        inv_keywords = dict((v, k) for k, v in grammar.keywords.items())
        dfa, state, nodes = tos

        def check():
            for first in dfa[1]:
                try:
                    yield inv_keywords[first]
                except KeyError:
                    yield tokenize.tok_name[inv_tokens[first]]

        return sorted(check())


class StackNode(object):
    def __init__(self, dfa):
        self.dfa = dfa
        self.nodes = []

    @property
    def nonterminal(self):
        return self.dfa.from_rule

    def __repr__(self):
        return '%s(%s, %s)' % (self.__class__.__name__, self.dfa, self.nodes)


def _token_to_transition(grammar, type_, value):
    # Map from token to label
    if type_.contains_syntax:
        # Check for reserved words (keywords)
        try:
            return grammar.reserved_syntax_strings[value]
        except KeyError:
            pass

    return type_



class BaseParser(object):
    """Parser engine.

    A Parser instance contains state pertaining to the current token
    sequence, and should not be used concurrently by different threads
    to parse separate token sequences.

    See python/tokenize.py for how to get input tokens by a string.

    When a syntax error occurs, error_recovery() is called.
    """

    node_map = {}
    default_node = tree.Node

    leaf_map = {
    }
    default_leaf = tree.Leaf

    def __init__(self, pgen_grammar, start_nonterminal='file_input', error_recovery=False):
        self._pgen_grammar = pgen_grammar
        self._start_nonterminal = start_nonterminal
        self._error_recovery = error_recovery

    def parse(self, tokens):
        first_dfa = self._pgen_grammar.nonterminal_to_dfas[self._start_nonterminal][0]
        self.stack = Stack([StackNode(first_dfa)])

        for type_, value, start_pos, prefix in tokens:
            self.add_token(type_, value, start_pos, prefix)

        while self.stack and self.stack[-1].dfa.is_final:
            self._pop()

        if self.stack:
            # We never broke out -- EOF is too soon -- Unfinished statement.
            # However, the error recovery might have added the token again, if
            # the stack is empty, we're fine.
            raise InternalParseError("incomplete input", type_, value, start_pos)
        return self.rootnode

    def error_recovery(self, pgen_grammar, stack, typ, value, start_pos, prefix,
                       add_token_callback):
        if self._error_recovery:
            raise NotImplementedError("Error Recovery is not implemented")
        else:
            error_leaf = tree.ErrorLeaf('TODO %s' % typ, value, start_pos, prefix)
            raise ParserSyntaxError('SyntaxError: invalid syntax', error_leaf)

    def convert_node(self, pgen_grammar, nonterminal, children):
        try:
            return self.node_map[nonterminal](children)
        except KeyError:
            return self.default_node(nonterminal, children)

    def convert_leaf(self, pgen_grammar, type_, value, prefix, start_pos):
        try:
            return self.leaf_map[type_](value, start_pos, prefix)
        except KeyError:
            return self.default_leaf(value, start_pos, prefix)

    def add_token(self, type_, value, start_pos, prefix):
        """Add a token; return True if this is the end of the program."""
        grammar = self._pgen_grammar
        stack = self.stack
        transition = _token_to_transition(grammar, type_, value)

        while True:
            try:
                plan = stack[-1].dfa.transition_to_plan[transition]
                break
            except KeyError:
                if stack[-1].dfa.is_final:
                    self._pop()
                else:
                    self.error_recovery(grammar, stack, type_,
                                        value, start_pos, prefix, self.add_token)
                    return
            except IndexError:
                raise InternalParseError("too much input", type_, value, start_pos)

        stack[-1].dfa = plan.next_dfa

        for push in plan.dfa_pushes:
            stack.append(StackNode(push))

        leaf = self.convert_leaf(grammar, type_, value, prefix, start_pos)
        stack[-1].nodes.append(leaf)

    def _pop(self):
        tos = self.stack.pop()
        # If there's exactly one child, return that child instead of
        # creating a new node.  We still create expr_stmt and
        # file_input though, because a lot of Jedi depends on its
        # logic.
        if len(tos.nodes) == 1:
            new_node = tos.nodes[0]
        else:
            new_node = self.convert_node(self._pgen_grammar, tos.dfa.from_rule, tos.nodes)

        try:
            self.stack[-1].nodes.append(new_node)
        except IndexError:
            # Stack is empty, set the rootnode.
            self.rootnode = new_node
