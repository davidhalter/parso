from contextlib import contextmanager
from parso.normalizer import Normalizer, Rule, NormalizerConfig


IMPORT_TYPES = ('import_name', 'import_from')

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


class BracketNode(object):
    SAME_INDENT_TYPE = object()
    NEWLINE_TYPE = object()

    def __init__(self, config, indentation_level, leaf):
        next_leaf = leaf.get_next_leaf()
        if '\n' in next_leaf.prefix:
            # This implies code like:
            # foobarbaz(
            #     a,
            #     b,
            # )
            self.bracket_indentation = config.indentation * indentation_level
            self.item_indentation = self.bracket_indentation + config.indentation
            self.type = self.NEWLINE_TYPE
        else:
            # Implies code like:
            # foobarbaz(
            #           a,
            #           b,
            #           )
            self.expected_end_indent = leaf.end_pos[1]
            if '\t' in config.indentation:
                self.bracket_indentation = None
            else:
                self.bracket_indentation =  ' ' * self.expected_end_indent
            self.item_indentation = self.bracket_indentation
            self.type = self.SAME_INDENT_TYPE


def _is_magic_name(name):
    return name.value.startswith('__') and name.value.startswith('__')


class PEP8Normalizer(Normalizer):
    def __init__(self, config):
        super(PEP8Normalizer, self).__init__(config)
        self._indentation_level = 0
        self._last_indentation_level = 0
        self._on_newline = True
        self._bracket_stack = []

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

        if typ in IMPORT_TYPES:
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

                        if c.type in IMPORT_TYPES or isinstance(c, Flow):
                            continue

                        self.add_issue(402, 'Module level import not at top of file', node)
                        break
                    else:
                        continue
                    break

        if typ == 'suite':
            self._indentation_level += 1
        yield
        if typ == 'suite':
            self._indentation_level -= 1

    def _check_tabs_spaces(self, leaf, indentation):
        if self._wrong_indentation_char in indentation:
            self.add_issue(101, 'Indentation contains ' + self._indentation_type, leaf)
            return True
        return False

    def normalize(self, leaf):
        value = leaf.value
        info = WhitespaceInfo(leaf)
        should_be_indenation = self._indentation_level * self._config.indentation
        if self._on_newline:
            if info.indentation != should_be_indenation:
                if not self._check_tabs_spaces(info.indentation_part, info.indentation):
                    s = '%s %s' % (len(self._config.indentation), self._indentation_type)
                    self.add_issue(111, 'Indentation is not a multiple of ' + s, leaf)
        elif info.newline_count:
            if self._bracket_stack:
                node = self._bracket_stack[-1]
                if value in '])}':
                    should_be_indenation = node.bracket_indentation
                else:
                    should_be_indenation = node.item_indentation
                if info.indentation != should_be_indenation:
                    if not self._check_tabs_spaces(info.indentation_part, info.indentation):
                        if len(info.indentation) < len(should_be_indenation):
                            if value in '])}':
                                self.add_issue(124, "Closing bracket does not match visual indentation", leaf)
                            else:
                                if node.type == BracketNode.SAME_INDENT_TYPE:
                                    self.add_issue(128, 'Continuation line under-indented for visual indent', leaf)
                                else:
                                    self.add_issue(121, 'Continuation line under-indented for hanging indent', leaf)
                        else:
                            if value in '])}':
                                self.add_issue(123, "Losing bracket does not match indentation of opening bracket's line", leaf)
                            else:
                                if node.type == BracketNode.SAME_INDENT_TYPE:
                                    self.add_issue(127, 'Continuation line over-indented for visual indent', leaf)
                                else:
                                    self.add_issue(126, 'Continuation line over-indented for hanging indent', leaf)
            # TODO  else?

        first = True
        for comment in info.comments:
            if first and not self._on_newline:
                continue
            first = False

            actual_len = len(comment.indentation)
            # Comments can be dedented. So we have to care for that.
            for i in range(self._last_indentation_level, self._indentation_level - 1, -1):
                should_be_indenation = i * self._config.indentation
                should_len = len(should_be_indenation)
                if actual_len >= should_len:
                    break


            if comment.indentation == should_be_indenation:
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

        # Finalize the state.
        if value and value in '()[]{}' and leaf.parent.type not in ('error_node', 'error_leaf'):
            if value in '([{':
                node = BracketNode(self._config, self._indentation_level, leaf)
                self._bracket_stack.append(node)
            else:
                self._bracket_stack.pop()

        self._on_newline = leaf.type == 'newline'
        self._last_indentation_level = self._indentation_level

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
