from parso.normalizer import Normalizer, Error


class CompressNormalizer(Normalizer):
    """
    Removes comments and whitespace.
    """
    def normalize(self, leaf):
        return leaf.prefix + leaf.value


class PEP8Normalizer(Normalizer):
    """
    Normalizing to PEP8. Not really implemented, yet.
    """
    def normalize(self, leaf):
        return leaf.value

    def iter_errors(self, leaf):
        return iter([])


class Rule():
    pass
