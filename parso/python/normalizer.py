from contextlib import contextmanager

from parso.normalizer import Normalizer, NormalizerConfig, Issue

_BLOCK_STMTS = ('if_stmt', 'while_stmt', 'for_stmt', 'try_stmt', 'with_stmt')
# This is the maximal block size given by python.
_MAX_BLOCK_SIZE = 20

class CompressNormalizer(Normalizer):
    """
    Removes comments and whitespace.
    """
    def normalize(self, leaf):
        return leaf.prefix + leaf.value


class Context(object):
    def __init__(self, scope, parent_context=None):
        self.blocks = []

    @contextmanager
    def add_block(self, node):
        self.blocks.append(node)
        yield
        self.blocks.pop()

    @contextmanager
    def add_context(self, node):
        self.blocks.append(node)
        yield Context(node, parent_context=self)
        self.blocks.pop()


class ErrorFinder(Normalizer):
    """
    Searches for errors in the syntax tree.
    """
    def __init__(self, *args, **kwargs):
        super(ErrorFinder, self).__init__(*args, **kwargs)
        self._error_dict = {}

    def initialize(self, node):
        from parso.python.tree import search_ancestor
        parent_scope = search_ancestor(node, 'classdef', 'funcdef', 'file_input')
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
