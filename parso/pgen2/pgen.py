# Copyright 2004-2005 Elemental Security, Inc. All Rights Reserved.
# Licensed to PSF under a Contributor Agreement.

# Modifications:
# Copyright David Halter and Contributors
# Modifications are dual-licensed: MIT and PSF.

"""
Specifying grammars in pgen is possible with this grammar::

    grammar: (NEWLINE | rule)* ENDMARKER
    rule: NAME ':' rhs NEWLINE
    rhs: items ('|' items)*
    items: item+
    item: '[' rhs ']' | atom ['+' | '*']
    atom: '(' rhs ')' | NAME | STRING

This grammar is self-referencing.
"""

from parso.pgen2.grammar import Grammar
from parso.python import token
from parso.python import tokenize
from parso.utils import parse_version_string


class ParserGenerator(object):
    def __init__(self, dfas, token_namespace):
        self._token_namespace = token_namespace
        self.dfas = dfas

    def make_grammar(self, grammar):
        self._first = {}  # map from symbol name to set of tokens
        self._addfirstsets()

        names = list(self.dfas.keys())
        names.sort()
        for name in names:
            i = 256 + len(grammar.symbol2number)
            grammar.symbol2number[name] = i
            grammar.number2symbol[i] = name
        for name in names:
            dfa = self.dfas[name]
            states = []
            for state in dfa:
                arcs = []
                for label, next in state.arcs.items():
                    arcs.append((self._make_label(grammar, label), dfa.index(next)))
                if state.isfinal:
                    arcs.append((0, dfa.index(state)))
                states.append(arcs)
            grammar.states.append(states)
            grammar.dfas[grammar.symbol2number[name]] = (states, self._make_first(grammar, name))
        return grammar

    def _make_first(self, grammar, name):
        rawfirst = self._first[name]
        first = {}
        for label in rawfirst:
            ilabel = self._make_label(grammar, label)
            ##assert ilabel not in first # XXX failed on <> ... !=
            first[ilabel] = 1
        return first

    def _make_label(self, grammar, label):
        # XXX Maybe this should be a method on a subclass of converter?
        ilabel = len(grammar.labels)
        if label[0].isalpha():
            # Either a symbol name or a named token
            if label in grammar.symbol2number:
                # A symbol name (a non-terminal)
                if label in grammar.symbol2label:
                    return grammar.symbol2label[label]
                else:
                    grammar.labels.append((grammar.symbol2number[label], None))
                    grammar.symbol2label[label] = ilabel
                    grammar.label2symbol[ilabel] = label
                    return ilabel
            else:
                # A named token (NAME, NUMBER, STRING)
                itoken = getattr(self._token_namespace, label, None)
                assert isinstance(itoken, int), label
                if itoken in grammar.tokens:
                    return grammar.tokens[itoken]
                else:
                    grammar.labels.append((itoken, None))
                    grammar.tokens[itoken] = ilabel
                    return ilabel
        else:
            # Either a keyword or an operator
            assert label[0] in ('"', "'"), label
            value = eval(label)
            if value[0].isalpha():
                # A keyword
                if value in grammar.keywords:
                    return grammar.keywords[value]
                else:
                    # TODO this might be an issue?! Using token.NAME here?
                    grammar.labels.append((token.NAME, value))
                    grammar.keywords[value] = ilabel
                    return ilabel
            else:
                # An operator (any non-numeric token)
                itoken = self._token_namespace.generate_token_id(value)
                if itoken in grammar.tokens:
                    return grammar.tokens[itoken]
                else:
                    grammar.labels.append((itoken, None))
                    grammar.tokens[itoken] = ilabel
                    return ilabel

    def _addfirstsets(self):
        names = list(self.dfas.keys())
        names.sort()
        for name in names:
            if name not in self._first:
                self._calcfirst(name)
            #print name, self._first[name].keys()

    def _calcfirst(self, name):
        dfa = self.dfas[name]
        self._first[name] = None  # dummy to detect left recursion
        state = dfa[0]
        totalset = {}
        overlapcheck = {}
        for label, next in state.arcs.items():
            if label in self.dfas:
                if label in self._first:
                    fset = self._first[label]
                    if fset is None:
                        raise ValueError("recursion for rule %r" % name)
                else:
                    self._calcfirst(label)
                    fset = self._first[label]
                totalset.update(fset)
                overlapcheck[label] = fset
            else:
                totalset[label] = 1
                overlapcheck[label] = {label: 1}
        inverse = {}
        for label, itsfirst in overlapcheck.items():
            for symbol in itsfirst:
                if symbol in inverse:
                    raise ValueError("rule %s is ambiguous; %s is in the"
                                     " first sets of %s as well as %s" %
                                     (name, symbol, label, inverse[symbol]))
                inverse[symbol] = label
        self._first[name] = totalset


class _GrammarParser():
    """
    The parser for Python grammar files.
    """
    def __init__(self, bnf_grammar):
        self._bnf_grammar = bnf_grammar
        self.generator = tokenize.tokenize(
            bnf_grammar,
            version_info=parse_version_string('3.6')
        )
        self._gettoken()  # Initialize lookahead

    def parse(self):
        dfas = {}
        start_symbol = None
        # grammar: (NEWLINE | rule)* ENDMARKER
        while self.type != token.ENDMARKER:
            while self.type == token.NEWLINE:
                self._gettoken()

            # rule: NAME ':' rhs NEWLINE
            self._current_rule_name = self._expect(token.NAME)
            self._expect(token.COLON)

            a, z = self._parse_rhs()
            self._expect(token.NEWLINE)

            #_dump_nfa(a, z)
            dfa = _make_dfa(a, z)
            #_dump_dfa(self._current_rule_name, dfa)
            # oldlen = len(dfa)
            _simplify_dfa(dfa)
            # newlen = len(dfa)
            dfas[self._current_rule_name] = dfa
            #print(self._current_rule_name, oldlen, newlen)

            if start_symbol is None:
                start_symbol = self._current_rule_name

        return dfas, start_symbol

    def _parse_rhs(self):
        # rhs: items ('|' items)*
        a, z = self._parse_alt()
        if self.value != "|":
            return a, z
        else:
            aa = NFAState(self._current_rule_name)
            zz = NFAState(self._current_rule_name)
            while True:
                # Add the possibility to go into the state of a and come back
                # to finish.
                aa.add_arc(a)
                z.add_arc(zz)
                if self.value != "|":
                    break

                self._gettoken()
                a, z = self._parse_alt()
            return aa, zz

    def _parse_alt(self):
        # items: item+
        a, b = self._parse_item()
        while self.type in (token.NAME, token.STRING, token.LPAR, token.LSQB):
            c, d = self._parse_item()
            # Need to end on the next item.
            b.add_arc(c)
            b = d
        return a, b

    def _parse_item(self):
        # item: '[' rhs ']' | atom ['+' | '*']
        if self.value == "[":
            self._gettoken()
            a, z = self._parse_rhs()
            self._expect(token.RSQB)
            # Make it also possible that there is no token and change the
            # state.
            a.add_arc(z)
            return a, z
        else:
            a, z = self._parse_atom()
            value = self.value
            if value not in ("+", "*"):
                return a, z
            self._gettoken()
            # Make it clear that we can go back to the old state and repeat.
            z.add_arc(a)
            if value == "+":
                return a, z
            else:
                # The end state is the same as the beginning, nothing must
                # change.
                return a, a

    def _parse_atom(self):
        # atom: '(' rhs ')' | NAME | STRING
        if self.value == "(":
            self._gettoken()
            a, z = self._parse_rhs()
            self._expect(token.RPAR)
            return a, z
        elif self.type in (token.NAME, token.STRING):
            a = NFAState(self._current_rule_name)
            z = NFAState(self._current_rule_name)
            # Make it clear that the state transition requires that value.
            a.add_arc(z, self.value)
            self._gettoken()
            return a, z
        else:
            self._raise_error("expected (...) or NAME or STRING, got %s/%s",
                              self.type, self.value)

    def _expect(self, type):
        if self.type != type:
            self._raise_error("expected %s(%s), got %s(%s)",
                              type, token.tok_name[type], self.type, self.value)
        value = self.value
        self._gettoken()
        return value

    def _gettoken(self):
        tup = next(self.generator)
        self.type, self.value, self.begin, prefix = tup

    def _raise_error(self, msg, *args):
        if args:
            try:
                msg = msg % args
            except:
                msg = " ".join([msg] + list(map(str, args)))
        line = self._bnf_grammar.splitlines()[self.begin[0] - 1]
        raise SyntaxError(msg, ('<grammar>', self.begin[0],
                                self.begin[1], line))


class NFAState(object):
    def __init__(self, from_rule):
        self.from_rule = from_rule
        self.arcs = []  # list of (label, NFAState) pairs

    def add_arc(self, next, label=None):
        assert label is None or isinstance(label, str)
        assert isinstance(next, NFAState)
        self.arcs.append((label, next))

    def __repr__(self):
        return '<%s: from %s>' % (self.__class__.__name__, self.from_rule)


class DFAState(object):
    def __init__(self, nfaset, final):
        assert isinstance(nfaset, dict)
        assert isinstance(next(iter(nfaset)), NFAState)
        assert isinstance(final, NFAState)
        self.nfaset = nfaset
        self.isfinal = final in nfaset
        self.arcs = {}  # map from label to DFAState

    def add_arc(self, next, label):
        assert isinstance(label, str)
        assert label not in self.arcs
        assert isinstance(next, DFAState)
        self.arcs[label] = next

    def unifystate(self, old, new):
        for label, next in self.arcs.items():
            if next is old:
                self.arcs[label] = new

    def __eq__(self, other):
        # Equality test -- ignore the nfaset instance variable
        assert isinstance(other, DFAState)
        if self.isfinal != other.isfinal:
            return False
        # Can't just return self.arcs == other.arcs, because that
        # would invoke this method recursively, with cycles...
        if len(self.arcs) != len(other.arcs):
            return False
        for label, next in self.arcs.items():
            if next is not other.arcs.get(label):
                return False
        return True

    __hash__ = None  # For Py3 compatibility.


def _simplify_dfa(dfas):
    # This is not theoretically optimal, but works well enough.
    # Algorithm: repeatedly look for two states that have the same
    # set of arcs (same labels pointing to the same nodes) and
    # unify them, until things stop changing.

    # dfas is a list of DFAState instances
    changes = True
    while changes:
        changes = False
        for i, state_i in enumerate(dfas):
            for j in range(i + 1, len(dfas)):
                state_j = dfas[j]
                if state_i == state_j:
                    #print "  unify", i, j
                    del dfas[j]
                    for state in dfas:
                        state.unifystate(state_j, state_i)
                    changes = True
                    break


def _make_dfa(start, finish):
    # To turn an NFA into a DFA, we define the states of the DFA
    # to correspond to *sets* of states of the NFA.  Then do some
    # state reduction.  Let's represent sets as dicts with 1 for
    # values.
    assert isinstance(start, NFAState)
    assert isinstance(finish, NFAState)

    def closure(state):
        base = {}
        addclosure(state, base)
        return base

    def addclosure(state, base):
        assert isinstance(state, NFAState)
        if state in base:
            return
        base[state] = 1
        for label, next in state.arcs:
            if label is None:
                addclosure(next, base)

    states = [DFAState(closure(start), finish)]
    for state in states:  # NB states grows while we're iterating
        arcs = {}
        for nfastate in state.nfaset:
            for label, next in nfastate.arcs:
                if label is not None:
                    addclosure(next, arcs.setdefault(label, {}))
        for label, nfaset in arcs.items():
            for st in states:
                if st.nfaset == nfaset:
                    break
            else:
                st = DFAState(nfaset, finish)
                states.append(st)
            state.add_arc(st, label)
    return states  # List of DFAState instances; first one is start


def _dump_nfa(start, finish):
    print("Dump of NFA for", start.from_rule)
    todo = [start]
    for i, state in enumerate(todo):
        print("  State", i, state is finish and "(final)" or "")
        for label, next in state.arcs:
            if next in todo:
                j = todo.index(next)
            else:
                j = len(todo)
                todo.append(next)
            if label is None:
                print("    -> %d" % j)
            else:
                print("    %s -> %d" % (label, j))


def _dump_dfa(name, dfa):
    print("Dump of DFA for", name)
    for i, state in enumerate(dfa):
        print("  State", i, state.isfinal and "(final)" or "")
        for label, next in state.arcs.items():
            print("    %s -> %d" % (label, dfa.index(next)))


def generate_grammar(bnf_grammar, token_namespace):
    """
    ``bnf_text`` is a grammar in extended BNF (using * for repetition, + for
    at-least-once repetition, [] for optional parts, | for alternatives and ()
    for grouping).

    It's not EBNF according to ISO/IEC 14977. It's a dialect Python uses in its
    own parser.
    """
    dfas, start_symbol = _GrammarParser(bnf_grammar).parse()
    p = ParserGenerator(dfas, token_namespace)
    return p.make_grammar(Grammar(bnf_grammar, start_symbol))
