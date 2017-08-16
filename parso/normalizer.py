from contextlib import contextmanager


class Normalizer(object):
    def __init__(self, grammar, config):
        self._grammar = grammar
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
    rule_value_map = {}
    rule_type_map = {}

    def create_normalizer(self, grammar):
        if self.normalizer_class is None:
            return None

        return self.normalizer_class(grammar, self)

    @classmethod
    def register_rule(cls, **kwargs):
        """
        Use it as a class decorator:

        >>> normalizer = NormalizerConfig()
        >>> @normalizer.register_rule(value='foo')
        ... class MyRule(Rule):
        ...     error_code = 42
        """
        return cls._register_rule(**kwargs)

    @classmethod
    def _register_rule(cls, value=None, type=None):
        if value is None and type is None:
            raise ValueError("You must register at least something.")

        def decorator(func):
            if value is not None:
                cls.rule_value_map[value] = func
            if type is not None:
                cls.rule_type_map[type] = func
            return func

        return decorator


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
    code = None
    message = None

    def __init__(self, normalizer):
        self._normalizer = normalizer

    def is_issue(self, node):
        raise NotImplementedError()

    def get_node(self, node):
        return node

    def add_issue(self, node, code=None, message=None):
        if code is None:
            code = self.code
            if code is None:
                raise ValueError("The error code on the class is not set.")

        if message is None:
            message = self.message
            if message is None:
                raise ValueError("The message on the class is not set.")

        self._normalizer.add_issue(code, message, node)

    def feed_node(self, node):
        if self.check(node):
            issue_node = self.get_node(node)
            self.add_issue(issue_node)
