# -*- coding: utf-8 -*-
import codecs
import warnings
import re
from contextlib import contextmanager

from parso.normalizer import Normalizer, NormalizerConfig, Issue

_BLOCK_STMTS = ('if_stmt', 'while_stmt', 'for_stmt', 'try_stmt', 'with_stmt')
_STAR_EXPR_PARENTS = ('testlist_star_expr', 'testlist_comp', 'exprlist')
# This is the maximal block size given by python.
_MAX_BLOCK_SIZE = 20
_MAX_INDENT_COUNT = 100
ALLOWED_FUTURES = (
    'all_feature_names', 'nested_scopes', 'generators', 'division',
    'absolute_import', 'with_statement', 'print_function', 'unicode_literals',
    # TODO make this one optional in lower python versions.
    'generator_stop'
)


def _is_bytes_literal(string):
    return 'b' in string.string_prefix.lower()


def _iter_stmts(scope):
    """
    Iterates over all statements and splits up  simple_stmt.
    """
    for child in scope.children:
        if child.type == 'simple_stmt':
            for child2 in child.children:
                if child2.type == 'newline' or child2 == ';':
                    continue
                yield child2
        else:
            yield child


def _get_comprehension_type(atom):
    first, second = atom.children[:2]
    if second.type == 'testlist_comp' and second.children[1].type == 'comp_for':
        if first == '[':
            return 'list comprehension'
        else:
            return 'generator expression'
    elif second.type == 'dictorsetmaker' and second.children[-1].type == 'comp_for':
        if second.children[1] == ':':
            return 'dict comprehension'
        else:
            return 'set comprehension'
    return None


def _is_future_import(import_from):
    # It looks like a __future__ import that is relative is still a future
    # import. That feels kind of odd, but whatever.
    # if import_from.level != 0:
        # return False
    from_names = import_from.get_from_names()
    return [n.value for n in from_names] == ['__future__']


def _remove_parens(atom):
    """
    Returns the inner part of an expression like `(foo)`. Also removes nested
    parens.
    """
    try:
        children = atom.children
    except AttributeError:
        pass
    else:
        if len(children) == 3 and children[0] == '(':
            return _remove_parens(atom.children[1])
    return atom


def _iter_params(parent_node):
    return (n for n in parent_node.children if n.type == 'param')


def _is_future_import_first(import_from):
    """
    Checks if the import is the first statement of a file.
    """
    found_docstring = False
    for stmt in _iter_stmts(import_from.get_root_node()):
        if stmt.type == 'string' and not found_docstring:
            continue
        found_docstring = True

        if stmt == import_from:
            return True
        if stmt.type == 'import_from' and _is_future_import(stmt):
            continue
        return False


class Context(object):
    def __init__(self, node, add_syntax_error, parent_context=None):
        self.node = node
        self.blocks = []
        self.parent_context = parent_context
        self._used_name_dict = {}
        self._global_names = []
        self._nonlocal_names = []
        self._nonlocal_names_in_subscopes = []
        self._add_syntax_error = add_syntax_error

    def is_async_funcdef(self):
        # Stupidly enough async funcdefs can have two different forms,
        # depending if a decorator is used or not.
        return self.is_function() \
            and self.node.parent.type in ('async_funcdef', 'async_stmt')

    def is_function(self):
        return self.node.type == 'funcdef'

    def add_name(self, name):
        parent_type = name.parent.type
        if parent_type == 'trailer':
            # We are only interested in first level names.
            return

        if parent_type == 'global_stmt':
            self._global_names.append(name)
        elif parent_type == 'nonlocal_stmt':
            self._nonlocal_names.append(name)
        else:
            self._used_name_dict.setdefault(name.value, []).append(name)

    def finalize(self):
        """
        Returns a list of nonlocal names that need to be part of that scope.
        """
        self._analyze_names(self._global_names, 'global')
        self._analyze_names(self._nonlocal_names, 'nonlocal')

        # Python2.6 doesn't have dict comprehensions.
        global_name_strs = dict((n.value, n) for n in self._global_names)
        for nonlocal_name in self._nonlocal_names:
            try:
                global_name = global_name_strs[nonlocal_name.value]
            except KeyError:
                continue

            message = "name '%s' is nonlocal and global" % global_name.value
            if global_name.start_pos < nonlocal_name.start_pos:
                error_name = global_name
            else:
                error_name = nonlocal_name
            self._add_syntax_error(message, error_name)

        nonlocals_not_handled = []
        for nonlocal_name in self._nonlocal_names_in_subscopes:
            search = nonlocal_name.value
            if search in global_name_strs or self.parent_context is None:
                message = "no binding for nonlocal '%s' found" % nonlocal_name.value
                self._add_syntax_error(message, nonlocal_name)
            elif not self.is_function() or \
                    nonlocal_name.value not in self._used_name_dict:
                nonlocals_not_handled.append(nonlocal_name)
        return self._nonlocal_names + nonlocals_not_handled

    def _analyze_names(self, globals_or_nonlocals, type_):
        def raise_(message):
            self._add_syntax_error(message % (base_name.value, type_), base_name)

        params = []
        if self.node.type == 'funcdef':
            params = self.node.params

        for base_name in globals_or_nonlocals:
            found_global_or_nonlocal = False
            # Somehow Python does it the reversed way.
            for name in reversed(self._used_name_dict.get(base_name.value, [])):
                if name.start_pos > base_name.start_pos:
                    # All following names don't have to be checked.
                    found_global_or_nonlocal = True

                parent = name.parent
                if parent.type == 'param' and parent.name == name:
                    # Skip those here, these definitions belong to the next
                    # scope.
                    continue

                if name.is_definition():
                    if parent.type == 'expr_stmt' \
                            and parent.children[1].type == 'annassign':
                        if found_global_or_nonlocal:
                            # If it's after the global the error seems to be
                            # placed there.
                            base_name = name
                        raise_("annotated name '%s' can't be %s")
                        break
                    else:
                        message = "name '%s' is assigned to before %s declaration"
                else:
                    message = "name '%s' is used prior to %s declaration"

                if not found_global_or_nonlocal:
                    raise_(message)
                    # Only add an error for the first occurence.
                    break

            for param in params:
                if param.name.value == base_name.value:
                    raise_("name '%s' is parameter and %s"),

    @contextmanager
    def add_block(self, node):
        self.blocks.append(node)
        yield
        self.blocks.pop()

    @contextmanager
    def add_context(self, node):
        new_context = Context(node, self._add_syntax_error, parent_context=self)
        yield new_context
        self._nonlocal_names_in_subscopes += new_context.finalize()


class ErrorFinder(Normalizer):
    """
    Searches for errors in the syntax tree.
    """
    def __init__(self, *args, **kwargs):
        super(ErrorFinder, self).__init__(*args, **kwargs)
        self._error_dict = {}
        self._version = self._grammar._version_int

    def initialize(self, node):
        from parso.python.tree import search_ancestor
        allowed = 'classdef', 'funcdef', 'file_input'
        if node.type in allowed:
            parent_scope = node
        else:
            parent_scope = search_ancestor(node, allowed)
        self._context = Context(parent_scope, self._add_syntax_error)
        self._indentation_count = 0

    @contextmanager
    def visit_node(self, node):
        if node.type == 'error_node':
            leaf = node.get_next_leaf()
            if node.children[-1].type == 'newline':
                # This is the beginning of a suite that is not indented.
                spacing = list(leaf._split_prefix())[-1]
                self._add_indentation_error('expected an indented block', spacing)
            else:
                if leaf.type != 'error_leaf':
                    # Error leafs will be added later as an error.
                    self._add_syntax_error("invalid syntax", leaf)
        elif node.type in _BLOCK_STMTS:
            if node.type == 'try_stmt':
                default_except = None
                for except_clause in node.children[3::3]:
                    if except_clause in ('else', 'finally'):
                        break
                    if except_clause == 'except':
                        default_except = except_clause
                    elif default_except is not None:
                        self._add_syntax_error("default 'except:' must be last", default_except)

            if node.type == 'for_stmt':
                # Some of the nodes here are already used, so no else if
                expr_list = node.children[1]
                if expr_list.type != 'expr_list':  # Already handled.
                    self._check_assignment(expr_list)

            with self._context.add_block(node):
                if len(self._context.blocks) == _MAX_BLOCK_SIZE:
                    self._add_syntax_error("too many statically nested blocks", node)
                yield
            return
        elif node.type in ('classdef', 'funcdef'):
            context = self._context
            with self._context.add_context(node) as new_context:
                self._context = new_context
                yield
                self._context = context
            return
        elif node.type == 'import_from' and _is_future_import(node):
            if not _is_future_import_first(node):
                message = "from __future__ imports must occur at the beginning of the file"
                self._add_syntax_error(message, node)

            for from_name, future_name in node.get_paths():
                name = future_name.value
                if name== 'braces':
                    message = "not a chance"
                    self._add_syntax_error(message, node)
                elif name == 'barry_as_FLUFL':
                    message = "Seriously I'm not implementing this :) ~ Dave"
                    self._add_syntax_error(message, node)
                elif name not in ALLOWED_FUTURES:
                    message = "future feature %s is not defined" % name
                    self._add_syntax_error(message, node)
        elif node.type == 'import_from':
            if node.is_star_import() and self._context.parent_context is not None:
                message = "import * only allowed at module level"
                self._add_syntax_error(message, node)
        elif node.type == 'import_as_names':
            if node.children[-1] == ',':
                # from foo import a,
                message = "trailing comma not allowed without surrounding parentheses"
                self._add_syntax_error(message, node)
        elif node.type in _STAR_EXPR_PARENTS:
            if node.parent.type == 'del_stmt':
                self._add_syntax_error("can't use starred expression here", node.parent)
            else:
                def is_definition(node, ancestor):
                    if ancestor is None:
                        return False

                    type_ = ancestor.type
                    if type_ == 'trailer':
                        return False

                    if type_ == 'expr_stmt':
                        return node.start_pos < ancestor.children[-1].start_pos

                    return is_definition(node, ancestor.parent)

                if is_definition(node, node.parent):
                    args = [c for c in node.children if c != ',']
                    starred = [c for c in args if c.type == 'star_expr']
                    if len(starred) > 1:
                        message = "two starred expressions in assignment"
                        self._add_syntax_error(message, starred[1])
                    elif starred:
                        count = args.index(starred[0])
                        if count >= 256:
                            message = "too many expressions in star-unpacking assignment"
                            self._add_syntax_error(message, starred[0])
        elif node.type == 'star_expr':
            if node.parent.type not in _STAR_EXPR_PARENTS:
                message = "starred assignment target must be in a list or tuple"
                self._add_syntax_error(message, node)
            if node.parent.type == 'testlist_comp':
                # [*[] for a in [1]]
                if node.parent.children[1].type == 'comp_for':
                    message = "iterable unpacking cannot be used in comprehension"
                    self._add_syntax_error(message, node)
        elif node.type == 'comp_for':
            # Some of the nodes here are already used, so no else if
            expr_list = node.children[1 + int(node.children[0] == 'async')]
            if expr_list.type != 'expr_list':  # Already handled.
                self._check_assignment(expr_list)

            if node.children[0] == 'async' \
                    and not self._context.is_async_funcdef():
                message = "asynchronous comprehension outside of an asynchronous function"
                self._add_syntax_error(message, node)
        elif node.type == 'arglist':
            first_arg = node.children[0]
            if first_arg.type == 'argument' \
                    and first_arg.children[1].type == 'comp_for':
                if len(node.children) >= 2:
                    # foo(x for x in [], b)
                    message = "Generator expression must be parenthesized if not sole argument"
                    self._add_syntax_error(message, node)
            else:
                arg_set = set()
                kw_only = False
                kw_unpacking_only = False
                is_old_starred = False
                # In python 3 this would be a bit easier (stars are part of
                # argument), but we have to understand both.
                for argument in node.children:
                    if argument == ',':
                        continue

                    if argument in ('*', '**'):
                        # Python < 3.5 has the order engraved in the grammar
                        # file.  No need to do anything here.
                        is_old_starred = True
                        continue
                    if is_old_starred:
                        is_old_starred = False
                        continue

                    if argument.type == 'argument':
                        first = argument.children[0]
                        if first in ('*', '**'):
                            if first == '*':
                                if kw_unpacking_only:
                                    # foo(**kwargs, *args)
                                    message = "iterable argument unpacking follows keyword argument unpacking"
                                    self._add_syntax_error(message, argument)
                            else:
                                kw_unpacking_only = True
                        else:  # Is a keyword argument.
                            kw_only = True
                            if first.type == 'name':
                                if first.value in arg_set:
                                    # f(x=1, x=2)
                                    message = "keyword argument repeated"
                                    self._add_syntax_error(message, first)
                                else:
                                    arg_set.add(first.value)
                    else:
                        if kw_unpacking_only:
                            # f(**x, y)
                            message = "positional argument follows keyword argument unpacking"
                            self._add_syntax_error(message, argument)
                        elif kw_only:
                            # f(x=2, y)
                            message = "positional argument follows keyword argument"
                            self._add_syntax_error(message, argument)
        elif node.type == 'atom':
            first = node.children[0]
            # e.g. 's' b''
            message = "cannot mix bytes and nonbytes literals"
            # TODO this check is only relevant for Python 3+
            if first.type == 'string':
                first_is_bytes = _is_bytes_literal(first)
                for string in node.children[1:]:
                    if first_is_bytes != _is_bytes_literal(string):
                        self._add_syntax_error(message, node)
                        break
        elif node.type in ('parameters', 'lambdef'):
            param_names = set()
            default_only = False
            for p in _iter_params(node):
                if p.name.value in param_names:
                    message = "duplicate argument '%s' in function definition"
                    self._add_syntax_error(message % p.name.value, p.name)
                param_names.add(p.name.value)

                if p.default is None:
                    if default_only:
                        # def f(x=3, y): pass
                        message = "non-default argument follows default argument"
                        self._add_syntax_error(message, node)
                else:
                    default_only = True
        elif node.type == 'annassign':
            # x, y: str
            type_ = None
            message = "only single target (not %s) can be annotated"
            lhs = node.parent.children[0]
            lhs = _remove_parens(lhs)
            try:
                children = lhs.children
            except AttributeError:
                pass
            else:
                if ',' in children or lhs.type == 'atom' and children[0] == '(':
                    type_ = 'tuple'
                elif lhs.type == 'atom' and children[0] == '[':
                    type_ = 'list'
                trailer = children[-1]

            if type_ is None:
                if not (lhs.type == 'name'
                        # subscript/attributes are allowed
                        or lhs.type in ('atom_expr', 'power')
                            and trailer.type == 'trailer'
                            and trailer.children[0] != '('):
                    # True: int
                    # {}: float
                    message = "illegal target for annotation"
                    self._add_syntax_error(message, lhs.parent)
            else:
                self._add_syntax_error(message % type_, lhs.parent)
        elif node.type == 'argument':
            first = node.children[0]
            if node.children[1] == '=' and first.type != 'name':
                if first.type == 'lambdef':
                    # f(lambda: 1=1)
                    message = "lambda cannot contain assignment"
                else:
                    # f(+x=1)
                    message = "keyword can't be an expression"
                self._add_syntax_error(message, first)
        elif node.type == 'nonlocal_stmt':
            if self._context.parent_context is None:
                message = "nonlocal declaration not allowed at module level"
                self._add_syntax_error(message, node)
            elif self._context.is_function():
                for nonlocal_name in node.children[1::2]:
                    param_names = [p.name.value for p in self._context.node.params]
                    if nonlocal_name.value == node:
                        pass
        elif node.type == 'expr_stmt':
            for before_equal in node.children[:-2:2]:
                self._check_assignment(before_equal)

            augassign = node.children[1]
            if augassign != '=' and augassign.type != 'annassign':  # Is augassign.
                if node.children[0].type in ('testlist_star_expr', 'atom', 'testlist'):
                    message = "illegal expression for augmented assignment"
                    self._add_syntax_error(message, node)
        elif node.type == 'with_item':
            self._check_assignment(node.children[2])
        elif node.type == 'del_stmt':
            child = node.children[1]
            if child.type != 'expr_list':  # Already handled.
                self._check_assignment(child, is_deletion=True)
        elif node.type == 'expr_list':
            for expr in node.children[::2]:
                self._check_assignment(expr)
        elif node.type == 'suite':
            self._indentation_count += 1
            if self._indentation_count == _MAX_INDENT_COUNT:
                self._add_indentation_error("too many levels of indentation", node.children[1])

        yield

    def visit_leaf(self, leaf):
        if leaf.type == 'error_leaf':
            if leaf.original_type in ('indent', 'error_dedent'):
                # Indents/Dedents itself never have a prefix. They are just
                # "pseudo" tokens that get removed by the syntax tree later.
                # Therefore in case of an error we also have to check for this.
                spacing = list(leaf.get_next_leaf()._split_prefix())[-1]
                if leaf.original_type == 'indent':
                    message = 'unexpected indent'
                else:
                    message = 'unindent does not match any outer indentation level'
                self._add_indentation_error(message, spacing)
            else:
                if leaf.value.startswith('\\'):
                    message = 'unexpected character after line continuation character'
                else:
                    match = re.match('\\w{,2}("{1,3}|\'{1,3})', leaf.value)
                    if match is None:
                        message = 'invalid syntax'
                    else:
                        if len(match.group(1)) == 1:
                            message = 'EOL while scanning string literal'
                        else:
                            message = 'EOF while scanning triple-quoted string literal'
                self._add_syntax_error(message, leaf)
        elif leaf.type == 'name':
            if leaf.value == '__debug__' and leaf.is_definition():
                if self._version < (3, 0):
                    message = 'cannot assign to __debug__'
                else:
                    message = 'assignment to keyword'
                self._add_syntax_error(message, leaf)
            if leaf.value == 'None' and self._version < (3, 0) and leaf.is_definition():
                self._add_syntax_error('cannot assign to None', leaf)

            self._context.add_name(leaf)
        elif leaf.type == 'string':
            string_prefix = leaf.string_prefix.lower()
            if 'b' in string_prefix \
                    and any(c for c in leaf.value if ord(c) > 127):
                # TODO add check for python 3
                # b'ä'
                message = "bytes can only contain ASCII literal characters."
                self._add_syntax_error(message, leaf)

            if 'r' not in string_prefix:
                # Raw strings don't need to be checked if they have proper
                # escaping.
                is_bytes = self._version < (3, 0)
                if 'b' in string_prefix:
                    is_bytes = True
                if 'u' in string_prefix:
                    is_bytes = False

                payload = leaf._get_payload()
                if is_bytes:
                    payload = payload.encode('utf-8')
                    func = codecs.escape_decode
                else:
                    func = codecs.unicode_escape_decode

                try:
                    with warnings.catch_warnings():
                        # The warnings from parsing strings are not relevant.
                        warnings.filterwarnings('ignore')
                        func(payload)
                except UnicodeDecodeError as e:
                    self._add_syntax_error('(unicode error) ' + str(e), leaf)
                except ValueError as e:
                    self._add_syntax_error('(value error) ' + str(e), leaf)

        elif leaf.value == 'continue':
            in_loop = False
            for block in self._context.blocks:
                if block.type == 'for_stmt':
                    in_loop = True
                if block.type == 'try_stmt':
                    last_block = block.children[-3]
                    if last_block == 'finally' and leaf.start_pos > last_block.start_pos:
                        message = "'continue' not supported inside 'finally' clause"
                        self._add_syntax_error(message, leaf)
            if not in_loop:
                message = "'continue' not properly in loop"
                self._add_syntax_error(message, leaf)
        elif leaf.value == 'break':
            in_loop = False
            for block in self._context.blocks:
                if block.type == 'for_stmt':
                    in_loop = True
            if not in_loop:
                self._add_syntax_error("'break' outside loop", leaf)
        elif leaf.value in ('yield', 'return'):
            if self._context.node.type != 'funcdef':
                self._add_syntax_error("'%s' outside function" % leaf.value, leaf.parent)
            elif self._context.is_async_funcdef() \
                    and any(self._context.node.iter_yield_exprs()):
                if leaf.value == 'return' and leaf.parent.type == 'return_stmt':
                    self._add_syntax_error("'return' with value in async generator", leaf.parent)
                elif leaf.value == 'yield' \
                        and leaf.get_next_leaf() != 'from' \
                        and self._version == (3, 5):
                    self._add_syntax_error("'yield' inside async function", leaf.parent)
        elif leaf.value == 'await':
            if not self._context.is_async_funcdef():
                self._add_syntax_error("'await' outside async function", leaf.parent)
        elif leaf.value == 'from' and leaf.parent.type == 'yield_arg' \
                and self._context.is_async_funcdef():
            yield_ = leaf.parent.parent
            self._add_syntax_error("'yield from' inside async function", yield_)
        elif leaf.value == '*':
            params = leaf.parent
            if params.type == 'parameters' and params:
                after = params.children[params.children.index(leaf) + 1:]
                after = [child for child in after
                         if child not in (',', ')') and not child.star_count]
                if len(after) == 0:
                    self._add_syntax_error("named arguments must follow bare *", leaf)
        elif leaf.value == '**':
            if leaf.parent.type == 'dictorsetmaker':
                comp_for = leaf.get_next_sibling().get_next_sibling()
                if comp_for is not None and comp_for.type == 'comp_for':
                    # {**{} for a in [1]}
                    message = "dict unpacking cannot be used in dict comprehension"
                    # TODO probably this should get a better end_pos including
                    # the next sibling of leaf.
                    self._add_syntax_error(message, leaf)

        return ''

    def _check_assignment(self, node, is_deletion=False):
        error = None
        type_ = node.type
        if type_ == 'lambdef':
            error = 'lambda'
        elif type_ == 'atom':
            first, second = node.children[:2]
            error = _get_comprehension_type(node)
            if error is None:
                if second.type in ('dictorsetmaker', 'string'):
                    error = 'literal'
                elif first in ('(', '['):
                    if second.type == 'yield_expr':
                        error = 'yield expression'
                    elif second.type == 'testlist_comp':
                        # This is not a comprehension, they were handled
                        # further above.
                        for child in second.children[::2]:
                            self._check_assignment(child, is_deletion)
                    else:  # Everything handled, must be useless brackets.
                        self._check_assignment(second, is_deletion)
        elif type_ == 'keyword':
            error = 'keyword'
        elif type_ == 'operator':
            if node.value == '...':
                error = 'Ellipsis'
        elif type_ == 'comparison':
            error = 'comparison'
        elif type_ in ('string', 'number'):
            error = 'literal'
        elif type_ == 'yield_expr':
            # This one seems to be a slightly different warning in Python.
            message = 'assignment to yield expression not possible'
            self._add_syntax_error(message, node)
        elif type_ == 'test':
            error = 'conditional expression'
        elif type_ in ('atom_expr', 'power'):
            if node.children[0] == 'await':
                error = 'await expression'
            elif node.children[-2] == '**':
                error = 'operator'
            else:
                # Has a trailer
                trailer = node.children[-1]
                assert trailer.type == 'trailer'
                if trailer.children[0] == '(':
                    error = 'function call'
        elif type_ in ('testlist_star_expr', 'exprlist', 'testlist'):
            for child in node.children[::2]:
                self._check_assignment(child, is_deletion)
        elif ('expr' in type_ and type_ != 'star_expr' # is a substring
              or '_test' in type_
              or type_ in ('term', 'factor')):
            error = 'operator'

        if error is not None:
            message = "can't %s %s" % ("delete" if is_deletion else "assign to", error)
            self._add_syntax_error(message, node)

    def _add_indentation_error(self, message, spacing):
        self._add_error(903, "IndentationError: " + message, spacing)

    def _add_syntax_error(self, message, node):
        self._add_error(901, "SyntaxError: " + message, node)

    def _add_error(self, code, message, node):
        # Check if the issues are on the same line.
        line = node.start_pos[0]
        args = (code, message, node)
        self._error_dict.setdefault(line, args)

    def finalize(self):
        self._context.finalize()

        for code, message, node in self._error_dict.values():
            self.issues.append(Issue(node, code, message))


class ErrorFinderConfig(NormalizerConfig):
    normalizer_class = ErrorFinder
