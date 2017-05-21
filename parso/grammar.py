import hashlib

from parso.pgen2.pgen import generate_grammar


class Grammar(object):
    def __init__(self, bnf_text, tokenizer, parser, diff_parser=None):
        self._pgen_grammar = generate_grammar(bnf_text)
        self._parser = parser
        self._tokenizer = tokenizer
        self._diff_parser = diff_parser
        self.sha256 = hashlib.sha256(bnf_text.encode("utf-8")).hexdigest()

    def __repr__(self):
        labels = self._pgen_grammar.symbol2number.values()
        txt = ' '.join(list(labels)[:3]) + ' ...'
        return '<%s:%s>' % (self.__class__.__name__, txt)
