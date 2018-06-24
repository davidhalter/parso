from parso.python import tree
from parso.python.token import PythonTokenTypes
from parso.parser import BaseParser
from parso.pgen2.parse import token_to_ilabel


NAME = PythonTokenTypes.NAME
INDENT = PythonTokenTypes.INDENT
DEDENT = PythonTokenTypes.DEDENT


class Parser(BaseParser):
    """
    This class is used to parse a Python file, it then divides them into a
    class structure of different scopes.

    :param pgen_grammar: The grammar object of pgen2. Loaded by load_grammar.
    """

    node_map = {
        'expr_stmt': tree.ExprStmt,
        'classdef': tree.Class,
        'funcdef': tree.Function,
        'file_input': tree.Module,
        'import_name': tree.ImportName,
        'import_from': tree.ImportFrom,
        'break_stmt': tree.KeywordStatement,
        'continue_stmt': tree.KeywordStatement,
        'return_stmt': tree.ReturnStmt,
        'raise_stmt': tree.KeywordStatement,
        'yield_expr': tree.YieldExpr,
        'del_stmt': tree.KeywordStatement,
        'pass_stmt': tree.KeywordStatement,
        'global_stmt': tree.GlobalStmt,
        'nonlocal_stmt': tree.KeywordStatement,
        'print_stmt': tree.KeywordStatement,
        'assert_stmt': tree.AssertStmt,
        'if_stmt': tree.IfStmt,
        'with_stmt': tree.WithStmt,
        'for_stmt': tree.ForStmt,
        'while_stmt': tree.WhileStmt,
        'try_stmt': tree.TryStmt,
        'comp_for': tree.CompFor,
        # Not sure if this is the best idea, but IMO it's the easiest way to
        # avoid extreme amounts of work around the subtle difference of 2/3
        # grammar in list comoprehensions.
        'list_for': tree.CompFor,
        # Same here. This just exists in Python 2.6.
        'gen_for': tree.CompFor,
        'decorator': tree.Decorator,
        'lambdef': tree.Lambda,
        'old_lambdef': tree.Lambda,
        'lambdef_nocond': tree.Lambda,
    }
    default_node = tree.PythonNode

    # Names/Keywords are handled separately
    _leaf_map = {
        PythonTokenTypes.STRING: tree.String,
        PythonTokenTypes.NUMBER: tree.Number,
        PythonTokenTypes.NEWLINE: tree.Newline,
        PythonTokenTypes.ENDMARKER: tree.EndMarker,
        PythonTokenTypes.FSTRING_STRING: tree.FStringString,
        PythonTokenTypes.FSTRING_START: tree.FStringStart,
        PythonTokenTypes.FSTRING_END: tree.FStringEnd,
    }

    def __init__(self, pgen_grammar, error_recovery=True, start_nonterminal='file_input'):
        super(Parser, self).__init__(pgen_grammar, start_nonterminal,
                                     error_recovery=error_recovery)

        self.syntax_errors = []
        self._omit_dedent_list = []
        self._indent_counter = 0

        # TODO do print absolute import detection here.
        # try:
        #     del python_grammar_no_print_statement.keywords["print"]
        # except KeyError:
        #     pass  # Doesn't exist in the Python 3 grammar.

        # if self.options["print_function"]:
        #     python_grammar = pygram.python_grammar_no_print_statement
        # else:

    def parse(self, tokens):
        if self._error_recovery:
            if self._start_nonterminal != 'file_input':
                raise NotImplementedError

            tokens = self._recovery_tokenize(tokens)

        node = super(Parser, self).parse(tokens)

        if self._start_nonterminal == 'file_input' != node.type:
            # If there's only one statement, we get back a non-module. That's
            # not what we want, we want a module, so we add it here:
            node = self.convert_node(
                self._pgen_grammar,
                'file_input',
                [node]
            )

        return node

    def convert_node(self, pgen_grammar, nonterminal, children):
        """
        Convert raw node information to a PythonBaseNode instance.

        This is passed to the parser driver which calls it whenever a reduction of a
        grammar rule produces a new complete node, so that the tree is build
        strictly bottom-up.
        """
        try:
            return self.node_map[nonterminal](children)
        except KeyError:
            if nonterminal == 'suite':
                # We don't want the INDENT/DEDENT in our parser tree. Those
                # leaves are just cancer. They are virtual leaves and not real
                # ones and therefore have pseudo start/end positions and no
                # prefixes. Just ignore them.
                children = [children[0]] + children[2:-1]
            elif nonterminal == 'list_if':
                # Make transitioning from 2 to 3 easier.
                nonterminal = 'comp_if'
            elif nonterminal == 'listmaker':
                # Same as list_if above.
                nonterminal = 'testlist_comp'
            return self.default_node(nonterminal, children)

    def convert_leaf(self, pgen_grammar, type, value, prefix, start_pos):
        # print('leaf', repr(value), token.tok_name[type])
        if type == NAME:
            if value in pgen_grammar.reserved_syntax_strings:
                return tree.Keyword(value, start_pos, prefix)
            else:
                return tree.Name(value, start_pos, prefix)

        return self._leaf_map.get(type, tree.Operator)(value, start_pos, prefix)

    def error_recovery(self, pgen_grammar, stack, typ, value, start_pos, prefix,
                       add_token_callback):
        tos_nodes = stack[-1].nodes
        if tos_nodes:
            last_leaf = tos_nodes[-1].get_last_leaf()
        else:
            last_leaf = None

        if self._start_nonterminal == 'file_input' and \
                (typ == PythonTokenTypes.ENDMARKER or
                 typ == DEDENT and '\n' not in last_leaf.value):
            def reduce_stack(states, newstate):
                # reduce
                state = newstate
                while states[state] == [(0, state)]:
                    self.pgen_parser._pop()

                    dfa, state, (type_, nodes) = stack[-1]
                    states, first = dfa

            # In Python statements need to end with a newline. But since it's
            # possible (and valid in Python ) that there's no newline at the
            # end of a file, we have to recover even if the user doesn't want
            # error recovery.
            if stack[-1].dfa.from_rule == 'simple_stmt':
                ilabel = token_to_ilabel(pgen_grammar, PythonTokenTypes.NEWLINE, value)
                try:
                    plan = stack[-1].dfa.ilabel_to_plan[ilabel]
                except KeyError:
                    pass
                else:
                    if plan.next_dfa.is_final and not plan.dfa_pushes:
                        # We are ignoring here that the newline would be
                        # required for a simple_stmt.
                        stack[-1].dfa = plan.next_dfa
                        add_token_callback(typ, value, start_pos, prefix)
                        return

        if not self._error_recovery:
            return super(Parser, self).error_recovery(
                pgen_grammar, stack, typ, value, start_pos, prefix,
                add_token_callback)

        def current_suite(stack):
            # For now just discard everything that is not a suite or
            # file_input, if we detect an error.
            one_line_suite = False
            for until_index, stack_node in reversed(list(enumerate(stack))):
                # `suite` can sometimes be only simple_stmt, not stmt.
                if one_line_suite:
                    break
                elif stack_node.nonterminal == 'file_input':
                    break
                elif stack_node.nonterminal == 'suite':
                    if len(stack_node.nodes) > 1:
                        break
                    elif not stack_node.nodes:
                        one_line_suite = True
                    # `suite` without an indent are error nodes.
            return until_index

        until_index = current_suite(stack)

        if self._stack_removal(stack, until_index + 1):
            add_token_callback(typ, value, start_pos, prefix)
        else:
            if typ == INDENT:
                # For every deleted INDENT we have to delete a DEDENT as well.
                # Otherwise the parser will get into trouble and DEDENT too early.
                self._omit_dedent_list.append(self._indent_counter)

            error_leaf = tree.PythonErrorLeaf(typ.name, value, start_pos, prefix)
            stack[-1].nodes.append(error_leaf)

        tos = stack[-1]
        if tos.nonterminal == 'suite':
            # Need at least one statement in the suite. This happend with the
            # error recovery above.
            try:
                tos.dfa = tos.dfa.arcs['stmt']
            except KeyError:
                # We're already in a final state.
                pass

    def _stack_removal(self, stack, start_index):
        all_nodes = []
        for stack_node in stack[start_index:]:
            all_nodes += stack_node.nodes
        if all_nodes:
            stack[start_index - 1].nodes.append(tree.PythonErrorNode(all_nodes))

        stack[start_index:] = []
        return bool(all_nodes)

    def _recovery_tokenize(self, tokens):
        for typ, value, start_pos, prefix in tokens:
            # print(tok_name[typ], repr(value), start_pos, repr(prefix))
            if typ == DEDENT:
                # We need to count indents, because if we just omit any DEDENT,
                # we might omit them in the wrong place.
                o = self._omit_dedent_list
                if o and o[-1] == self._indent_counter:
                    o.pop()
                    continue

                self._indent_counter -= 1
            elif typ == INDENT:
                self._indent_counter += 1
            yield typ, value, start_pos, prefix
