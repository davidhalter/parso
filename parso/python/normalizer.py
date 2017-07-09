from contextlib import contextmanager

from parso.normalizer import Normalizer, NormalizerConfig


class CompressNormalizer(Normalizer):
    """
    Removes comments and whitespace.
    """
    def normalize(self, leaf):
        return leaf.prefix + leaf.value


class ErrorFinder(Normalizer):
    """
    Searches for errors in the syntax tree.
    """
    def __init__(self, *args, **kwargs):
        super(ErrorFinder, self).__init__(*args, **kwargs)
        self._error_dict = {}

    @contextmanager
    def visit_node(self, node):
        if node.type == 'error_node':
            leaf = node.get_next_leaf()
            self._add_error(901, "Syntax Error", leaf)

        yield

    def visit_leaf(self, leaf):
        if leaf.type == 'error_leaf':
            self._add_error(901, "Syntax Error", leaf)

        return ''

    def _add_error(self, code, message, node):
        line = node.start_pos[0]
        self._error_dict.setdefault(line, (code, message, node))

    def finalize(self):
        for code, message, node in self._error_dict.values():
            self.add_issue(code, message, node)

    def add_issue(self, code, message, node):
        # Check if the issues are on the same line.
        prev = node.get_previous_leaf()
        if prev is not None and prev.type == 'error_leaf':
            # There's already an error nearby. There's a huge chance they are
            # related, so don't report this one.
            return

        super(ErrorFinder, self).add_issue(code, message, node)


class ErrorFinderConfig(NormalizerConfig):
    normalizer_class = ErrorFinder
