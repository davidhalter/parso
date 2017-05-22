import hashlib

from parso.pgen2.pgen import generate_grammar
from parso.utils import splitlines, source_to_unicode
from parso.python.parser import Parser, remove_last_newline
from parso.python.diff import DiffParser
from parso.tokenize import generate_tokens
from parso.cache import parser_cache, load_module, save_module


class Grammar(object):
    def __init__(self, bnf_text, tokenizer, parser, diff_parser=None):
        self._pgen_grammar = generate_grammar(bnf_text)
        self._parser = parser
        self._tokenizer = tokenizer
        self._diff_parser = diff_parser
        self._sha256 = hashlib.sha256(bnf_text.encode("utf-8")).hexdigest()

    def parse(self, code=None, **kwargs):
        """
        If you want to parse a Python file you want to start here, most likely.

        If you need finer grained control over the parsed instance, there will be
        other ways to access it.

        :param code: A unicode string that contains Python code.
        :param path: The path to the file you want to open. Only needed for caching.
        :param grammar: A Python grammar file, created with load_grammar. You may
            not specify it. In that case it's the current Python version.
        :param error_recovery: If enabled, any code will be returned. If it is
            invalid, it will be returned as an error node. If disabled, you will
            get a ParseError when encountering syntax errors in your code.
        :param start_symbol: The grammar symbol that you want to parse. Only
            allowed to be used when error_recovery is disabled.
        :param cache_path: If given saves the parso cache in this directory. If not
            given, defaults to the default cache places on each platform.

        :return: A syntax tree node. Typically the module.
        """
        return self._parse(code=code, **kwargs)

    def _parse(self, code=None, path=None, error_recovery=True,
               start_symbol='file_input', cache=False, diff_cache=False,
               cache_path=None):
        """
        Wanted python3.5 * operator and keyword only arguments. Therefore just
        wrap it all.
        """
        if code is None and path is None:
            raise TypeError("Please provide either code or a path.")

        if cache and code is None and path is not None:
            # With the current architecture we cannot load from cache if the
            # code is given, because we just load from cache if it's not older than
            # the latest change (file last modified).
            module_node = load_module(self, path, cache_path=cache_path)
            if module_node is not None:
                return module_node

        if code is None:
            with open(path, 'rb') as f:
                code = source_to_unicode(f.read())

        lines = tokenize_lines = splitlines(code, keepends=True)
        if diff_cache:
            try:
                module_cache_item = parser_cache[path]
            except KeyError:
                pass
            else:
                module_node = module_cache_item.node
                old_lines = module_cache_item.lines
                if old_lines == lines:
                    # TODO remove this line? I think it's not needed. (dave)
                    save_module(self, path, module_node, lines, pickling=False,
                                cache_path=cache_path)
                    return module_node

                new_node = DiffParser(self._pgen_grammar, module_node).update(
                    old_lines=old_lines,
                    new_lines=lines
                )
                save_module(self, path, new_node, lines, pickling=cache,
                            cache_path=cache_path)
                return new_node

        added_newline = not code.endswith('\n')
        if added_newline:
            code += '\n'
            tokenize_lines = list(tokenize_lines)
            tokenize_lines[-1] += '\n'
            tokenize_lines.append('')

        tokens = generate_tokens(tokenize_lines, use_exact_op_types=True)

        p = Parser(self._pgen_grammar, error_recovery=error_recovery, start_symbol=start_symbol)
        root_node = p.parse(tokens=tokens)
        if added_newline:
            remove_last_newline(root_node)

        if cache or diff_cache:
            save_module(self, path, root_node, lines, pickling=cache,
                        cache_path=cache_path)
        return root_node

    def __repr__(self):
        labels = self._pgen_grammar.symbol2number.values()
        txt = ' '.join(list(labels)[:3]) + ' ...'
        return '<%s:%s>' % (self.__class__.__name__, txt)
