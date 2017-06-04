from contextlib import contextmanager


class Normalizer(object):
    def __init__(self, config):
        self._config = config
        self.issues = []

    @contextmanager
    def visit_node(self):
        yield

    def normalize(self, leaf):
        return leaf.prefix + leaf.value

    def add_issue(self, code, message, node):
        issue = Issue(node, code, message)
        self.issues.append(issue)


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


class Rule(object):
    error_code = None
    message = None
    type = None
