from contextlib import contextmanager


class Normalizer(object):
    def __init__(self, config):
        self._config = config
        self.issues = []

    def walk(self, node):
        self.initialize(node)
        value = self.visit(node)
        self.finalize()
        return value

    def visit(self, node):
        try:
            children = node.children
        except AttributeError:
            return self.visit_leaf(node)
        else:
           with self.visit_node(node):
               return ''.join(self.visit(child) for child in children)

    @contextmanager
    def visit_node(self, node):
        yield

    def visit_leaf(self, leaf):
        return leaf.prefix + leaf.value

    def initialize(self, node):
        pass

    def finalize(self):
        pass

    def add_issue(self, code, message, node):
        issue = Issue(node, code, message)
        if issue not in self.issues:
            self.issues.append(issue)
        return True


class NormalizerConfig(object):
    normalizer_class = Normalizer

    def create_normalizer(self):
        if self.normalizer_class is None:
            return None

        return self.normalizer_class(self)

    @classmethod
    def register_rule(cls, rule):
        """
        Use it as a class decorator:

        >>> normalizer = NormalizerConfig()
        >>> @normalizer.register_rule
        ... class MyRule(Rule):
        ...     error_code = 42
        """
        try:
            rules = cls.rules
        except AttributeError:
            rules = cls.rules = []
        rules.append(rule)
        return rule


class Issue(object):
    def __init__(self, node, code, message):
        self._node = node
        self.code = code
        self.message = message
        self.start_pos = node.start_pos

    def __eq__(self, other):
        return self.start_pos == other.start_pos and self.code == other.code

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.code, self.start_pos))

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.code)



class Rule(object):
    error_code = None
    message = None
    type = None
