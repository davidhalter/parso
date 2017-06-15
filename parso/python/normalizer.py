from contextlib import contextmanager
from parso.normalizer import Normalizer, Rule, NormalizerConfig


_IMPORT_TYPES = ('import_name', 'import_from')
_SUITE_INTRODUCERS = ('classdef', 'funcdef', 'if_stmt', 'while_stmt',
                      'for_stmt', 'try_stmt', 'with_stmt')
_OPENING_BRACKETS = '([{'

class CompressNormalizer(Normalizer):
    """
    Removes comments and whitespace.
    """
    def normalize(self, leaf):
        return leaf.prefix + leaf.value


class Comment(object):
    def __init__(self, comment_part, indentation_part):
        self.comment_part = comment_part
        self.indentation_part = indentation_part
        if indentation_part is None:
            self.indentation = ''
        else:
            self.indentation = indentation_part.value
        self.start_pos = self.comment_part.start_pos


class WhitespaceInfo(object):
    def __init__(self, leaf):
        parts = list(leaf._split_prefix())
        '''
    ' ': 'spaces',
    '#': 'comment',
    '\\': 'backslash',
    '\f': 'formfeed',
    '\n': 'newline',
    '\r': 'newline',
    '\t': 'tabs',
'''
        self.has_backslash = False
        self.comments = []
        indentation_part = None
        self.newline_count = 0
        for part in parts:
            if part.type == 'backslash':
                self.has_backslash = True
                self.newline_count += 1

            if part.type == 'comment':
                self.comments.append(Comment(part, indentation_part))

            if part.type == 'indentation':
                indentation_part = part
            else:
                indentation_part = None

            if part.type == 'newline':
                self.newline_count += 1

        if indentation_part is None:
            self.indentation = ''
        else:
            self.indentation = indentation_part.value
        self.indentation_part = indentation_part

        self.trailing_whitespace = []
        self.comment_whitespace = []


class IndentationNode(object):
    SAME_INDENT_TYPE = object()
    NEWLINE_TYPE = object()
    BACKSLASH_TYPE = object()
    SUITE_TYPE = object()

    type = SUITE_TYPE

    def __init__(self, config, indentation_level):
        self.bracket_indentation = self.indentation = config.indentation * indentation_level


class BracketNode(IndentationNode):
    def __init__(self, config, parent_indentation, leaf):
        self.leaf = leaf

        next_leaf = leaf.get_next_leaf()
        if '\n' in next_leaf.prefix:
            # This implies code like:
            # foobarbaz(
            #     a,
            #     b,
            # )
            self.bracket_indentation = parent_indentation
            self.indentation = parent_indentation + config.indentation
            self.type = self.NEWLINE_TYPE
        else:
            # Implies code like:
            # foobarbaz(
            #           a,
            #           b,
            #           )
            self.expected_end_indent = leaf.end_pos[1]
            if '\t' in config.indentation:
                self.indentation = None
            else:
                self.indentation =  ' ' * self.expected_end_indent
            self.bracket_indentation = self.indentation
            self.type = self.SAME_INDENT_TYPE


class BackslashNode(IndentationNode):
    type = IndentationNode.BACKSLASH_TYPE

    def __init__(self, config, parent_indentation):
        self.bracket_indentation = self.indentation = parent_indentation + config.indentation


def _is_magic_name(name):
    return name.value.startswith('__') and name.value.startswith('__')


class PEP8Normalizer(Normalizer):
    def __init__(self, config):
        super(PEP8Normalizer, self).__init__(config)
        self._last_indentation_level = 0
        self._on_newline = True
        self._indentation_stack = [IndentationNode(config, indentation_level=0)]
        self._in_suite_introducer = False

        if ' ' in config.indentation:
            self._indentation_type = 'spaces'
            self._wrong_indentation_char = '\t'
        else:
            self._indentation_type = 'tabs'
            self._wrong_indentation_char = ' '

    @contextmanager
    def visit_node(self, node):
        typ = node.type

        if typ in 'import_name':
            names = node.get_defined_names()
            if len(names) > 1:
                for name in names[:1]:
                    self.add_issue(401, 'Multiple imports on one line', name)
        elif typ == 'lambdef':
            expr_stmt = node.parent
            # Check if it's simply defining a single name, not something like
            # foo.bar or x[1], where using a lambda could make more sense.
            if expr_stmt.type == 'expr_stmt' and any(n.type == 'name' for n in expr_stmt.children[:-2:2]):
                self.add_issue(731, 'Do not assign a lambda expression, use a def', node)
        elif typ == 'try_stmt':
            for child in node.children:
                # Here we can simply check if it's an except, because otherwise
                # it would be an except_clause.
                if child.type == 'keyword' and child.value == 'except':
                    self.add_issue(722, 'Do not use bare except, specify exception instead', child)
        elif typ == 'comparison':
            for child in node.children:
                if child.type not in ('atom_expr', 'power'):
                    continue
                if len(child.children) > 2:
                    continue
                trailer = child.children[1]
                atom = child.children[0]
                if trailer.type == 'trailer' and atom.type == 'name' \
                        and atom.value == 'type':
                    self.add_issue(721, "Do not compare types, use 'isinstance()", node)
                    break

        if typ in _IMPORT_TYPES:
            simple_stmt = node.parent
            module = simple_stmt.parent
            #if module.type == 'simple_stmt':
            if module.type == 'file_input':
                index = module.children.index(simple_stmt)
                from parso.python.tree import Flow
                for child in module.children[:index]:
                    children = [child]
                    if child.type == 'simple_stmt':
                        # Remove the newline.
                        children = child.children[:-1]
                    for c in children:
                        if c.type == 'expr_stmt' and \
                                all(_is_magic_name(n) for n in c.get_defined_names()):
                            continue

                        if c.type in _IMPORT_TYPES or isinstance(c, Flow):
                            continue

                        self.add_issue(402, 'Module level import not at top of file', node)
                        break
                    else:
                        continue
                    break

        in_introducer = typ in _SUITE_INTRODUCERS
        if in_introducer:
            self._in_suite_introducer = True

        if typ == 'suite':
            if self._indentation_stack[-1].type == IndentationNode.BACKSLASH_TYPE:
                self._indentation_stack.pop()

            self._indentation_stack.append(
                IndentationNode(self._config, len(self._indentation_stack))
            )
        yield
        if typ == 'suite':
            assert self._indentation_stack[-1].type == IndentationNode.SUITE_TYPE
            self._indentation_stack.pop()

        if in_introducer:
            self._in_suite_introducer = False

    def _check_tabs_spaces(self, leaf, indentation):
        if self._wrong_indentation_char in indentation:
            self.add_issue(101, 'Indentation contains ' + self._indentation_type, leaf)
            return True
        return False

    def normalize(self, leaf):
        value = leaf.value
        info = WhitespaceInfo(leaf)

        node = self._indentation_stack[-1]
        if info.has_backslash and node.type != IndentationNode.BACKSLASH_TYPE:
            if node.type != IndentationNode.SUITE_TYPE:
                self.add_issue(502, 'The backslash is redundant between brackets', leaf)
            else:
                node = BackslashNode(
                        self._config,
                        self._indentation_stack[-1].indentation
                    )
                self._indentation_stack.append(node)


        if self._on_newline:
            if self._indentation_stack and \
                    self._indentation_stack[-1].type == BackslashNode.BACKSLASH_TYPE:
                self._indentation_stack.pop()
            if info.indentation != node.indentation:
                if not self._check_tabs_spaces(info.indentation_part, info.indentation):
                    s = '%s %s' % (len(self._config.indentation), self._indentation_type)
                    self.add_issue(111, 'Indentation is not a multiple of ' + s, leaf)
        elif info.newline_count:
            if True:
                if value in '])}':
                    should_be_indentation = node.bracket_indentation
                else:
                    should_be_indentation = node.indentation
                if info.indentation != should_be_indentation:
                    if not self._check_tabs_spaces(info.indentation_part, info.indentation):
                        if value in '])}':
                            if node.type == IndentationNode.SAME_INDENT_TYPE:
                                self.add_issue(124, "Closing bracket does not match visual indentation", leaf)
                            else:
                                self.add_issue(123, "Losing bracket does not match indentation of opening bracket's line", leaf)
                        else:
                            if len(info.indentation) < len(should_be_indentation):
                                if node.type == IndentationNode.SAME_INDENT_TYPE:
                                    self.add_issue(128, 'Continuation line under-indented for visual indent', leaf)
                                elif node.type == IndentationNode.BACKSLASH_TYPE:
                                    self.add_issue(122, 'Continuation line missing indentation or outdented', leaf)
                                else:
                                    self.add_issue(121, 'Continuation line under-indented for hanging indent', leaf)
                            else:
                                if node.type == IndentationNode.SAME_INDENT_TYPE:
                                    self.add_issue(127, 'Continuation line over-indented for visual indent', leaf)
                                else:
                                    self.add_issue(126, 'Continuation line over-indented for hanging indent', leaf)

                elif self._in_suite_introducer and \
                        info.indentation == node.indentation:
                    self.add_issue(129, "Line with same indent as next logical line", leaf)

        first = True
        for comment in info.comments:
            if first and not self._on_newline:
                continue
            first = False

            actual_len = len(comment.indentation)
            # Comments can be dedented. So we have to care for that.
            for i in range(self._last_indentation_level, len(self._indentation_stack) - 2, -1):
                should_be_indentation = i * self._config.indentation
                should_len = len(should_be_indentation)
                if actual_len >= should_len:
                    break


            if comment.indentation == should_be_indentation:
                self._last_indentation_level = i
            else:
                if not self._check_tabs_spaces(comment.indentation_part, comment.indentation):
                    if actual_len < should_len:
                        self.add_issue(115, 'Expected an indented block (comment)', comment)
                    elif actual_len > should_len:
                        self.add_issue(116, 'Unexpected indentation (comment)', comment)
                    else:
                        self.add_issue(114, 'indentation is not a multiple of four (comment)', comment)

            self._on_newline = True

        self._analyse_non_prefix(leaf)

        # -------------------------------
        # Finalizing. Updating the state.
        # -------------------------------
        if value and value in '()[]{}' and leaf.type != 'error_leaf' \
                and leaf.parent.type != 'error_node':
            if value in _OPENING_BRACKETS:
                # Figure out here what the indentation is. For chained brackets
                # we can basically use the previous indentation.
                previous_leaf = leaf
                index = 1
                while not info.newline_count:
                    previous_leaf = previous_leaf.get_previous_leaf()
                    n = self._indentation_stack[-index]
                    if not isinstance(n, BracketNode) or previous_leaf != n.leaf:
                        break
                    index += 1
                indentation = self._indentation_stack[-index].indentation

                self._indentation_stack.append(
                    BracketNode(
                        self._config, indentation,
                        leaf
                    )
                )
            else:
                self._indentation_stack.pop()

        self._on_newline = leaf.type == 'newline'
        # TODO does this work? with brackets and stuff?
        self._last_indentation_level = len(self._indentation_stack)
        if self._on_newline and \
                self._indentation_stack[-1].type == IndentationNode.BACKSLASH_TYPE:
            self._indentation_stack.pop()

        if value == ':' and leaf.parent.type in _SUITE_INTRODUCERS:
            self._in_suite_introducer = False

        return value


    def _analyse_non_prefix(self, leaf):
        typ = leaf.type
        if typ == 'name' and leaf.value in ('l', 'O', 'I'):
            if leaf.is_definition():
                message = "Do not define %s named 'l', 'O', or 'I' one line"
                if leaf.parent.type == 'class' and leaf.parent.name == leaf:
                    self.add_issue(742, message % 'classes', leaf)
                elif leaf.parent.type == 'function' and leaf.parent.name == leaf:
                    self.add_issue(743, message % 'function', leaf)
                else:
                    self.add_issuadd_issue(741, message % 'variables', leaf)
        if leaf.value == ':':
            from parso.python.tree import Flow, Scope
            if isinstance(leaf.parent, (Flow, Scope)) and leaf.parent.type != 'lambdef':
                next_leaf = leaf.get_next_leaf()
                if next_leaf.type != 'newline':
                    if leaf.parent.type == 'funcdef':
                        self.add_issue(704, 'Multiple statements on one line (def)', next_leaf)
                    else:
                        self.add_issue(701, 'Multiple statements on one line (colon)', next_leaf)
        if leaf.value == ';':
            if leaf.get_next_leaf().type in ('newline', 'endmarker'):
                self.add_issue(703, 'Statement ends with a semicolon', leaf)
            else:
                self.add_issue(702, 'Multiple statements on one line (semicolon)', leaf)
        if leaf.value in ('==', '!='):
            comparison = leaf.parent
            index = comparison.children.index(leaf)
            left = comparison.children[index - 1]
            right = comparison.children[index + 1]
            for node in left, right:
                if node.type == 'keyword' or node.type == 'name':
                    if node.value == 'None':
                        message = "comparison to None should be 'if cond is None:'"
                        self.add_issue(711, message, leaf)
                        break
                    elif node.value in ('True', 'False'):
                        message = "comparison to False/True should be 'if cond is True:' or 'if cond:'"
                        self.add_issue(712, message, leaf)
                        break
        if leaf.value in ('in', 'is'):
            comparison = leaf.parent
            if comparison.type == 'comparison' and comparison.parent.type == 'not_test':
                if leaf.value == 'in':
                    self.add_issue(713, "test for membership should be 'not in'", leaf)
                else:
                    self.add_issue(714, "test for object identity should be 'is not'", leaf)

        return leaf.value

    def add_issue(self, code, message, node):
        try:
            parent = node.parent
        except AttributeError:
            # TODO for prefix parts, there's no parents yet.
            pass
        else:
            while parent:
                if parent.type == 'error_node':
                    return
                parent = parent.parent
        super(PEP8Normalizer, self).add_issue(code, message, node)


class PEP8NormalizerConfig(NormalizerConfig):
    normalizer_class = PEP8Normalizer
    """
    Normalizing to PEP8. Not really implemented, yet.
    """
    def __init__(self):
        self.indentation = ' ' * 4


@PEP8NormalizerConfig.register_rule
class FooRule(Rule):
    pass


@PEP8NormalizerConfig.register_rule
class BlankLineAtEnd(Rule):
    code = 'W391'
    message = 'blank line at end of file'

    leaf_event = ['endmarker']
