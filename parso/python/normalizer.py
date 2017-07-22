from contextlib import contextmanager

from parso.normalizer import Normalizer, NormalizerConfig, Issue

_BLOCK_STMTS = ('if_stmt', 'while_stmt', 'for_stmt', 'try_stmt', 'with_stmt')
_STAR_EXPR_PARENTS = ('testlist_star_expr', 'testlist_comp', 'exprlist')
# This is the maximal block size given by python.
_MAX_BLOCK_SIZE = 20

class CompressNormalizer(Normalizer):
    """
    Removes comments and whitespace.
    """
    def normalize(self, leaf):
        return leaf.prefix + leaf.value


def _iter_stmts(scope):
    """
    Iterates over all statements and splits up  simple_stmt.
    """
    for child in scope.children:
        if child.type == 'simple_stmt':
            for child2 in child.children:
                if child2.type == 'newline' or child2 == ';':
                    continue
                yield child2
        else:
            yield child


def _is_future_import(import_from):
    if import_from.level != 0:
        return False
    from_names = import_from.get_from_names()
    return [n.value for n in from_names] == ['__future__']


def _is_future_import_first(import_from):
    """
    Checks if the import is the first statement of a file.
    """
    found_docstring = False
    for stmt in _iter_stmts(import_from.get_root_node()):
        if stmt.type == 'string' and not found_docstring:
            continue
        found_docstring = True

        if stmt == import_from:
            return True
        if stmt.type == 'import_from' and _is_future_import(stmt):
            continue
        return False


class Context(object):
    def __init__(self, node, parent_context=None):
        self.node = node
        self.blocks = []
        self.parent_context = parent_context

    def is_async_funcdef(self):
        # Stupidly enough async funcdefs can have two different forms,
        # depending if a decorator is used or not.
        return self.node.type == 'funcdef' \
            and self.node.parent.type in ('async_funcdef', 'async_stmt')

    @contextmanager
    def add_block(self, node):
        self.blocks.append(node)
        yield
        self.blocks.pop()

    @contextmanager
    def add_context(self, node):
        yield Context(node, parent_context=self)


class ErrorFinder(Normalizer):
    """
    Searches for errors in the syntax tree.
    """
    def __init__(self, *args, **kwargs):
        super(ErrorFinder, self).__init__(*args, **kwargs)
        self._error_dict = {}

    def initialize(self, node):
        from parso.python.tree import search_ancestor
        allowed = 'classdef', 'funcdef', 'file_input'
        if node.type in allowed:
            parent_scope = node
        else:
            parent_scope = search_ancestor(node, allowed)
        self._context = Context(parent_scope)

    @contextmanager
    def visit_node(self, node):
        if node.type == 'error_node':
            leaf = node.get_next_leaf()
            if node.children[-1].type == 'newline':
                # This is the beginning of a suite that is not indented.
                spacing = list(leaf._split_prefix())[-1]
                self._add_indentation_error('expected an indented block', spacing)
            else:
                self._add_syntax_error("invalid syntax", leaf)
        elif node.type in _BLOCK_STMTS:
            if node.type == 'try_stmt':
                default_except = None
                for except_clause in node.children[3::3]:
                    if except_clause in ('else', 'finally'):
                        break
                    if except_clause == 'except':
                        default_except = except_clause
                    elif default_except is not None:
                        self._add_syntax_error("default 'except:' must be last", default_except)

            with self._context.add_block(node):
                if len(self._context.blocks) == _MAX_BLOCK_SIZE:
                    self._add_syntax_error("too many statically nested blocks", node)
                yield
            return
        elif node.type in ('classdef', 'funcdef'):
            context = self._context
            with self._context.add_context(node) as new_context:
                self._context = new_context
                yield
                self._context = context
            return
        elif node.type == 'import_from' \
                and _is_future_import(node) and not _is_future_import_first(node):
            message = "from __future__ imports must occur at the beginning of the file"
            self._add_syntax_error(message, node)
        elif node.type in _STAR_EXPR_PARENTS:
            if node.parent.type == 'del_stmt':
                self._add_syntax_error("can't use starred expression here", node.parent)
            else:
                starred = [c for c in node.children if c.type == 'star_expr']
                if len(starred) > 1:
                    message = "two starred expressions in assignment"
                    self._add_syntax_error(message, starred[1])
                    "can't use starred expression here"
        elif node.type == 'star_expr':
            if node.parent.type not in _STAR_EXPR_PARENTS:
                message = "starred assignment target must be in a list or tuple"
                self._add_syntax_error(message, node)
        elif node.type == 'comp_for':
            if node.children[0] == 'async' \
                    and not self._context.is_async_funcdef():
                message = "asynchronous comprehension outside of an asynchronous function"
                self._add_syntax_error(message, node)

        yield

    def visit_leaf(self, leaf):
        if leaf.type == 'error_leaf':
            if leaf.original_type in ('indent', 'error_dedent'):
                # Indents/Dedents itself never have a prefix. They are just
                # "pseudo" tokens that get removed by the syntax tree later.
                # Therefore in case of an error we also have to check for this.
                spacing = list(leaf.get_next_leaf()._split_prefix())[-1]
                if leaf.original_type == 'indent':
                    message = 'unexpected indent'
                else:
                    message = 'unindent does not match any outer indentation level'
                self._add_indentation_error(message, spacing)
            else:
                self._add_syntax_error('invalid syntax', leaf)
        elif leaf.value == 'continue':
            in_loop = False
            for block in self._context.blocks:
                if block.type == 'for_stmt':
                    in_loop = True
                if block.type == 'try_stmt':
                    last_block = block.children[-3]
                    if last_block == 'finally' and leaf.start_pos > last_block.start_pos:
                        message = "'continue' not supported inside 'finally' clause"
                        self._add_syntax_error(message, leaf)
            if not in_loop:
                message = "'continue' not properly in loop"
                self._add_syntax_error(message, leaf)
        elif leaf.value == 'break':
            in_loop = False
            for block in self._context.blocks:
                if block.type == 'for_stmt':
                    in_loop = True
            if not in_loop:
                self._add_syntax_error("'break' outside loop", leaf)
        elif leaf.value in ('yield', 'return'):
            if self._context.node.type != 'funcdef':
                self._add_syntax_error("'%s' outside function" % leaf.value, leaf.parent)
            elif self._context.is_async_funcdef() and leaf.value == 'return' \
                    and leaf.parent.type == 'return_stmt' \
                    and any(self._context.node.iter_yield_exprs()):
                self._add_syntax_error("'return' with value in async generator", leaf.parent)
        elif leaf.value == 'await':
            if not self._context.is_async_funcdef():
                self._add_syntax_error("'await' outside async function", leaf.parent)
        elif leaf.value == 'from' and leaf.parent.type == 'yield_arg' \
                and self._context.is_async_funcdef():
            yield_ = leaf.parent.parent
            self._add_syntax_error("'yield from' inside async function", yield_)
        elif leaf.value == '*':
            params = leaf.parent
            if params.type == 'parameters' and params:
                after = params.children[params.children.index(leaf) + 1:]
                after = [child for child in after if child not in (',', ')')]
                if len(after) == 0:
                    self._add_syntax_error("named arguments must follow bare *", leaf)
        return ''

    def _add_indentation_error(self, message, spacing):
        self._add_error(903, "IndentationError: " + message, spacing)

    def _add_syntax_error(self, message, node):
        self._add_error(901, "SyntaxError: " + message, node)

    def _add_error(self, code, message, node):
        # Check if the issues are on the same line.
        line = node.start_pos[0]
        self._error_dict.setdefault(line, (code, message, node))

    def finalize(self):
        for code, message, node in self._error_dict.values():
            self.issues.append(Issue(node, code, message))


class ErrorFinderConfig(NormalizerConfig):
    normalizer_class = ErrorFinder
