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

    def __init__(self, bnf_text, start_nonterminal):
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
