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
            self._add_syntax_error("Syntax Error", leaf)
        elif node.type in _BLOCK_STMTS:
            with self._context.add_block(node):
                yield
            return
        elif node.type in ('classdef', 'funcdef'):
            context = self._context
            with self._context.add_context(node) as new_context:
                if len(context.blocks) == _MAX_BLOCK_SIZE:
                    self._add_syntax_error("Too many statically nested blocks", node)
                self._context = new_context
                yield
                self._context = context
            return

        yield

    def visit_leaf(self, leaf):
        if leaf.type == 'error_leaf':
            self._add_syntax_error("Syntax Error", leaf)

        return ''

    def _add_syntax_error(self, message, node):
        self._add_error(901, message, node)

    def _add_error(self, code, message, node):
        # Check if the issues are on the same line.
        line = node.start_pos[0]
        self._error_dict.setdefault(line, (code, message, node))

    def finalize(self):
        for code, message, node in self._error_dict.values():
            self.issues.append(Issue(node, code, message))


class ErrorFinderConfig(NormalizerConfig):
    normalizer_class = ErrorFinder
