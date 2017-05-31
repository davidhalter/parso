import hashlib
import os
import sys
import re

from parso._compatibility import FileNotFoundError, unicode
from parso.pgen2.pgen import generate_grammar
from parso.utils import splitlines, source_to_unicode
from parso.python.diff import DiffParser
from parso.tokenize import tokenize_lines
from parso.cache import parser_cache, load_module, save_module
from parso.parser import BaseParser
from parso.python.parser import Parser as PythonParser

_loaded_grammars = {}


class Grammar(object):
    """
    Create custom grammars by calling this. It's not really supported, yet.

    :param text: A BNF representation of your grammar.
    """
    def __init__(self, text, tokenizer, parser=BaseParser,
                 diff_parser=None):
        self._pgen_grammar = generate_grammar(text)
        self._parser = parser
        self._tokenizer = tokenizer
        self._diff_parser = diff_parser
        self._hashed = hashlib.sha256(text.encode("utf-8")).hexdigest()

    def parse(self, code=None, **kwargs):
        """
        If you want to parse a Python file you want to start here, most likely.

        If you need finer grained control over the parsed instance, there will be
        other ways to access it.

        :param code str: A unicode string that contains Python code.
        :param path str: The path to the file you want to open. Only needed for caching.
        :param error_recovery bool: If enabled, any code will be returned. If
            it is invalid, it will be returned as an error node. If disabled,
            you will get a ParseError when encountering syntax errors in your
            code.
        :param start_symbol str: The grammar symbol that you want to parse. Only
            allowed to be used when error_recovery is False.
        :param cache bool: Keeps a copy of the parser tree in RAM and on disk
            if a path is given. Returns the cached trees if the corresponding
            files on disk have not changed.
        :param diff_cache bool: Diffs the cached python module against the new
            code and tries to parse only the parts that have changed. Returns
            the same (changed) module that is found in cache. Using this option
            requires you to not do anything anymore with the old cached module,
            because the contents of it might have changed.
        :param cache_path bool: If given saves the parso cache in this
            directory. If not given, defaults to the default cache places on
            each platform.

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
        if error_recovery and start_symbol != 'file_input':
            raise NotImplementedError("This is currently not implemented.")

        if cache and code is None and path is not None:
            # With the current architecture we cannot load from cache if the
            # code is given, because we just load from cache if it's not older than
            # the latest change (file last modified).
            module_node = load_module(self._hashed, path, cache_path=cache_path)
            if module_node is not None:
                return module_node

        if code is None:
            with open(path, 'rb') as f:
                code = source_to_unicode(f.read())

        lines = splitlines(code, keepends=True)
        if diff_cache:
            if self._diff_parser is None:
                raise TypeError("You have to define a diff parser to be able "
                                "to use this option.")
            try:
                module_cache_item = parser_cache[self._hashed][path]
            except KeyError:
                pass
            else:
                module_node = module_cache_item.node
                old_lines = module_cache_item.lines
                if old_lines == lines:
                    return module_node

                new_node = self._diff_parser(self._pgen_grammar, module_node).update(
                    old_lines=old_lines,
                    new_lines=lines
                )
                save_module(self._hashed, path, new_node, lines, pickling=cache,
                            cache_path=cache_path)
                return new_node

        tokens = self._tokenizer(lines)

        p = self._parser(self._pgen_grammar, error_recovery=error_recovery, start_symbol=start_symbol)
        root_node = p.parse(tokens=tokens)

        if cache or diff_cache:
            save_module(self._hashed, path, root_node, lines, pickling=cache,
                        cache_path=cache_path)
        return root_node

    def __repr__(self):
        labels = self._pgen_grammar.symbol2number.values()
        txt = ' '.join(list(labels)[:3]) + ' ...'
        return '<%s:%s>' % (self.__class__.__name__, txt)


def _parse_version(version):
    match = re.match(r'(\d+)(?:\.(\d)(?:\.\d+)?)?$', version)
    if match is None:
        raise ValueError('The given version is not in the right format. '
                         'Use something like "3.2" or "3".')

    major = match.group(1)
    minor = match.group(2)
    if minor is None:
        # Use the latest Python in case it's not exactly defined, because the
        # grammars are typically backwards compatible?
        if major == "2":
            minor = "7"
        elif major == "3":
            minor = "6"
        else:
            raise NotImplementedError("Sorry, no support yet for those fancy new/old versions.")
    return int(major + minor)


def load_grammar(version=None):
    """
    Loads a Python grammar. The default version is the current Python version.

    If you need support for a specific version, please use e.g.
    `version='3.3'`.
    """
    if version is None:
        version = '%s.%s' % sys.version_info[:2]
    if not isinstance(version, (unicode, str)):
        raise TypeError("version must be a string like 3.2.")

    version_int = _parse_version(version)

    # For these versions we use the same grammar files, because nothing
    # changed.
    if version_int == 33:
        version_int = 34
    elif version_int == 26:
        version_int = 27

    file = 'python/grammar' + str(version_int) + '.txt'

    global _loaded_grammars
    path = os.path.join(os.path.dirname(__file__), file)
    try:
        return _loaded_grammars[path]
    except KeyError:
        try:
            with open(path) as f:
                bnf_text = f.read()

            grammar = Grammar(
                bnf_text,
                tokenizer=tokenize_lines,
                parser=PythonParser,
                diff_parser=DiffParser
            )
            return _loaded_grammars.setdefault(path, grammar)
        except FileNotFoundError:
            message = "Python version %s is currently not supported." % version
            raise NotImplementedError(message)
