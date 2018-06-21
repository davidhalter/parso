# Copyright 2004-2005 Elemental Security, Inc. All Rights Reserved.
# Licensed to PSF under a Contributor Agreement.

# Modifications:
# Copyright David Halter and Contributors
# Modifications are dual-licensed: MIT and PSF.

"""This module defines the data structures used to represent a grammar.

These are a bit arcane because they are derived from the data
structures used by Python's 'pgen' parser generator.

There's also a table here mapping operators to their names in the
token module; the Python tokenize module reports all operators as the
fallback token code OP, but the parser needs the actual token code.

"""

from parso.python import token


class DFAPlan(object):
    def __init__(self, next_dfa, dfa_pushes=[]):
        self.next_dfa = next_dfa
        self.dfa_pushes = dfa_pushes

    def __repr__(self):
        return '%s(%s, %s)' % (self.__class__.__name__, self.next_dfa, self.dfa_pushes)


class Grammar(object):
    """Pgen parsing tables conversion class.

    Once initialized, this class supplies the grammar tables for the
    parsing engine implemented by parse.py.  The parsing engine
    accesses the instance variables directly.  The class here does not
    provide initialization of the tables; several subclasses exist to
    do this (see the conv and pgen modules).

    The instance variables are as follows:

    nonterminal2number --
                     A dict mapping nonterminal names to numbers.
                     Nonterminal numbers are always 256 or higher, to
                     distinguish them from token numbers, which are between 0
                     and 255 (inclusive).

    number2nonterminal --
                     A dict mapping numbers to nonterminal names;
                     these two are each other's inverse.

    states        -- a list of DFAs, where each DFA is a list of
                     states, each state is a list of arcs, and each
                     arc is a (i, j) pair where i is a label and j is
                     a state number.  The DFA number is the index into
                     this list.  (This name is slightly confusing.)
                     Final states are represented by a special arc of
                     the form (0, j) where j is its own state number.

    dfas          -- a dict mapping nonterminal numbers to (DFA, first)
                     pairs, where DFA is an item from the states list
                     above, and first is a set of tokens that can
                     begin this grammar rule (represented by a dict
                     whose values are always 1).

    labels        -- a list of (x, y) pairs where x is either a token
                     number or a nonterminal number, and y is either None
                     or a string; the strings are keywords.  The label
                     number is the index in this list; label numbers
                     are used to mark state transitions (arcs) in the
                     DFAs.

    start         -- the number of the grammar's start nonterminal.

    keywords      -- a dict mapping keyword strings to arc labels.

    tokens        -- a dict mapping token numbers to arc labels.

    """

    def __init__(self, bnf_grammar, start_nonterminal, rule_to_dfas, token_namespace):
        self._token_namespace = token_namespace
        self._nonterminal_to_dfas = rule_to_dfas

        self.nonterminal2number = {}
        self.number2nonterminal = {}
        self.states = []
        self.dfas = {}
        self.labels = [(0, "EMPTY")]
        self.keywords = {}
        self.tokens = {}
        self.nonterminal2label = {}
        self.label2nonterminal = {}
        self.start_nonterminal = start_nonterminal

        self._label_cache = {}
        self._make_grammar()

    def _make_grammar(self):
        # Map from grammar rule (nonterminal) name to a set of tokens.
        self._first_terminals = {}
        self._first_plans = {}

        nonterminals = list(self._nonterminal_to_dfas.keys())
        nonterminals.sort()
        for nonterminal in nonterminals:
            if nonterminal not in self._first_terminals:
                self._calculate_first_terminals(nonterminal)

            i = 256 + len(self.nonterminal2number)
            self.nonterminal2number[nonterminal] = i
            self.number2nonterminal[i] = nonterminal

        # Now that we have calculated the first terminals, we are sure that
        # there is no left recursion or ambiguities.

        for nonterminal in nonterminals:
            dfas = self._nonterminal_to_dfas[nonterminal]
            states = []
            for state in dfas:
                arcs = []
                for terminal_or_nonterminal, next_ in state.arcs.items():
                    arcs.append((self._make_label(terminal_or_nonterminal), dfas.index(next_)))
                if state.is_final:
                    arcs.append((0, dfas.index(state)))
                states.append(arcs)
            self.states.append(states)
            self.dfas[self.nonterminal2number[nonterminal]] = (states, self._make_first(nonterminal))

        for dfas in self._nonterminal_to_dfas.values():
            for dfa_state in dfas:
                dfa_state.ilabel_to_plan = plans = {}
                for terminal_or_nonterminal, next_dfa in dfa_state.arcs.items():
                    if terminal_or_nonterminal in self.nonterminal2number:
                        for t, pushes in self._first_plans[terminal_or_nonterminal].items():
                            plans[self._make_label(t)] = DFAPlan(next_dfa, pushes)
                    else:
                        ilabel = self._make_label(terminal_or_nonterminal)
                        plans[ilabel] = DFAPlan(next_dfa)

    def _make_first(self, nonterminal):
        rawfirst = self._first_terminals[nonterminal]
        first = set()
        for terminal_or_nonterminal in rawfirst:
            ilabel = self._make_label(terminal_or_nonterminal)
            ##assert ilabel not in first, "%s failed on <> ... !=" % terminal_or_nonterminal
            first.add(ilabel)
        return first

    def _cache_labels(func):
        def wrapper(self, label):
            try:
                return self._label_cache[label]
            except KeyError:
                result = func(self, label)
                self._label_cache[label] = result
                return result

        return wrapper

    #@_cache_labels
    def _make_label(self, label):
        # XXX Maybe this should be a method on a subclass of converter?
        ilabel = len(self.labels)
        if label[0].isalpha():
            # Either a nonterminal name or a named token
            if label in self.nonterminal2number:
                # A nonterminal name
                if label in self.nonterminal2label:
                    return self.nonterminal2label[label]
                else:
                    self.labels.append((self.nonterminal2number[label], None))
                    self.nonterminal2label[label] = ilabel
                    self.label2nonterminal[ilabel] = label
                    return ilabel
            else:
                # A named token (NAME, NUMBER, STRING)
                itoken = getattr(self._token_namespace, label, None)
                assert isinstance(itoken, int), label
                if itoken in self.tokens:
                    return self.tokens[itoken]
                else:
                    self.labels.append((itoken, None))
                    self.tokens[itoken] = ilabel
                    return ilabel
        else:
            # Either a keyword or an operator
            assert label[0] in ('"', "'"), label
            # TODO use literal_eval instead of a simple eval.
            value = eval(label)
            if value[0].isalpha():
                # A keyword
                if value in self.keywords:
                    return self.keywords[value]
                else:
                    self.labels.append((token.NAME, value))
                    self.keywords[value] = ilabel
                    return ilabel
            else:
                # An operator (any non-numeric token)
                itoken = self._token_namespace.generate_token_id(value)
                if itoken in self.tokens:
                    return self.tokens[itoken]
                else:
                    self.labels.append((itoken, None))
                    self.tokens[itoken] = ilabel
                    return ilabel

    def _calculate_first_terminals(self, nonterminal):
        dfas = self._nonterminal_to_dfas[nonterminal]
        self._first_terminals[nonterminal] = None  # dummy to detect left recursion
        self._first_plans[nonterminal] = {}
        # We only need to check the first dfa. All the following ones are not
        # interesting to find first terminals.
        state = dfas[0]
        totalset = set()
        overlapcheck = {}
        for nonterminal_or_string, next_ in state.arcs.items():
            if nonterminal_or_string in self._nonterminal_to_dfas:
                # It's a nonterminal and we have either a left recursion issue
                # in the grammar or we have to recurse.
                try:
                    fset = self._first_terminals[nonterminal_or_string]
                except KeyError:
                    self._calculate_first_terminals(nonterminal_or_string)
                    fset = self._first_terminals[nonterminal_or_string]
                else:
                    if fset is None:
                        raise ValueError("left recursion for rule %r" % nonterminal)
                totalset.update(fset)
                overlapcheck[nonterminal_or_string] = fset

                for t, pushes in self._first_plans[nonterminal_or_string].items():
                    assert not self._first_plans[nonterminal].get(t)
                    self._first_plans[nonterminal][t] = [next_] + pushes
            else:
                # It's a string. We have finally found a possible first token.
                totalset.add(nonterminal_or_string)
                overlapcheck[nonterminal_or_string] = set([nonterminal_or_string])
                self._first_plans[nonterminal][nonterminal_or_string] = [next_]

        inverse = {}
        for nonterminal_or_string, first_set in overlapcheck.items():
            for terminal in first_set:
                if terminal in inverse:
                    raise ValueError("rule %s is ambiguous; %s is in the"
                                     " first sets of %s as well as %s" %
                                     (nonterminal, terminal, nonterminal_or_string, inverse[terminal]))
                inverse[terminal] = nonterminal_or_string
        self._first_terminals[nonterminal] = totalset

    @property
    def start(self):
        return self.nonterminal2number[self.start_nonterminal]

    def report(self):
        """Dump the grammar tables to standard output, for debugging."""
        from pprint import pprint
        print("s2n")
        pprint(self.nonterminal2number)
        print("n2s")
        pprint(self.number2nonterminal)
        print("states")
        pprint(self.states)
        print("dfas")
        pprint(self.dfas)
        print("labels")
        pprint(self.labels)
        print("start", self.start)
