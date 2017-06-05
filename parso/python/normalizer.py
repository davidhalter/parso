from contextlib import contextmanager
from parso.normalizer import Normalizer, Rule, NormalizerConfig


IMPORT_TYPES = ('import_name', 'import_from')

class CompressNormalizer(Normalizer):
    """
    Removes comments and whitespace.
    """
    def normalize(self, leaf):
        return leaf.prefix + leaf.value


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
        for part in parts:
            if part.type:
                part
        self.newline_count = 2
        self.indentation = '  '
        self.trailing_whitespace = []
        self.comment_whitespace = []


def _is_magic_name(name):
    return name.value.startswith('__') and name.value.startswith('__')


class PEP8Normalizer(Normalizer):
    def __init__(self, config):
        super(PEP8Normalizer, self).__init__(config)
        self.indentation = 0

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
                if child.type != 'atom_expr':
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
            self.indentation += 1
        yield
        if typ == 'suite':
            self.indentation -= 1

    def normalize(self, leaf):
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

        for part in leaf._split_prefix():
            part
        return leaf.value


class PEP8NormalizerConfig(NormalizerConfig):
    normalizer_class = PEP8Normalizer
    """
    Normalizing to PEP8. Not really implemented, yet.
    """


@PEP8NormalizerConfig.register_rule
class FooRule(Rule):
    pass


@PEP8NormalizerConfig.register_rule
class BlankLineAtEnd(Rule):
    code = 'W391'
    message = 'blank line at end of file'

    leaf_event = ['endmarker']
