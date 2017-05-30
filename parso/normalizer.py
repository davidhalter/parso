class Normalizer(object):
    @classmethod
    def register_rule(cls, rule):
        """
        Use it as a class decorator:

        >>> normalizer = Normalizer()
        >>> @normalizer.register_rule
        >>> class MyRule(Rule):
        >>>     error_code = 42
        """
        try:
            rules = cls.rules
        except AttributeError:
            rules = cls.rules = []
        rules.append(rule)
        return rule

    def normalize(self, leaf):
        return leaf.prefix + leaf.value

    def iter_errors(self, leaf):
        return iter([])


class Error(object):
    def __init__(self, leaf, code, message):
        self._leaf = leaf
        self.code = code
        self.message = message


class Rule(object):
    error_code = None
    message = None
    type = None
