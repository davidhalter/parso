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
    """

    def __init__(self, start_nonterminal, rule_to_dfas, reserved_syntax_strings):
        self.nonterminal_to_dfas = rule_to_dfas

        self.reserved_syntax_strings = reserved_syntax_strings
        self.start_nonterminal = start_nonterminal

        self._make_grammar()

    def _make_grammar(self):
        # Map from grammar rule (nonterminal) name to a set of tokens.
        self._first_plans = {}

        nonterminals = list(self.nonterminal_to_dfas.keys())
        nonterminals.sort()
        for nonterminal in nonterminals:
            if nonterminal not in self._first_plans:
                self._calculate_first_terminals(nonterminal)

        # Now that we have calculated the first terminals, we are sure that
        # there is no left recursion or ambiguities.

        for dfas in self.nonterminal_to_dfas.values():
            for dfa_state in dfas:
                for nonterminal, next_dfa in dfa_state.nonterminal_arcs.items():
                    for transition, pushes in self._first_plans[nonterminal].items():
                        dfa_state.ilabel_to_plan[transition] = DFAPlan(next_dfa, pushes)

    def _calculate_first_terminals(self, nonterminal):
        dfas = self.nonterminal_to_dfas[nonterminal]
        new_first_plans = {}
        self._first_plans[nonterminal] = None  # dummy to detect left recursion
        # We only need to check the first dfa. All the following ones are not
        # interesting to find first terminals.
        state = dfas[0]
        for nonterminal2, next_ in state.nonterminal_arcs.items():
            # It's a nonterminal and we have either a left recursion issue
            # in the grammar or we have to recurse.
            try:
                first_plans2 = self._first_plans[nonterminal2]
            except KeyError:
                first_plans2 = self._calculate_first_terminals(nonterminal2)
            else:
                if first_plans2 is None:
                    raise ValueError("left recursion for rule %r" % nonterminal)

            for t, pushes in first_plans2.items():
                check = new_first_plans.get(t)
                if check is not None:
                    raise ValueError(
                        "Rule %s is ambiguous; %s is the"
                        " start of the rule %s as well as %s."
                        % (nonterminal, t, nonterminal2, check[-1].from_rule)
                    )
                new_first_plans[t] = [next_] + pushes

        for transition, next_ in state.ilabel_to_plan.items():
            # It's a string. We have finally found a possible first token.
            new_first_plans[transition] = [next_.next_dfa]

        self._first_plans[nonterminal] = new_first_plans
        return new_first_plans
