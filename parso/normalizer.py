class Normalizer():
    def normalize(self, leaf):
        return leaf.prefix + leaf.value

    def iter_errors(self, leaf):
        return iter([])


class Error():
    def __init__(self, leaf, code, message):
        self._leaf = leaf
        self.code = code
        self.message = message
