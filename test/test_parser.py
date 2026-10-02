# -*- coding: utf-8 -*-
from textwrap import dedent

import pytest

from parso import parse, ParserSyntaxError
from parso.python import tree
from parso.utils import split_lines


def test_basic_parsing(each_version):
    def compare(string):
        """Generates the AST object and then regenerates the code."""
        assert parse(string, version=each_version).get_code() == string

    compare('\na #pass\n')
    compare('wblabla* 1\t\n')
    compare('def x(a, b:3): pass\n')
    compare('assert foo\n')


def test_subscope_names(each_version):
    def get_sub(source):
        return parse(source, version=each_version).children[0]

    name = get_sub('class Foo: pass').name
    assert name.start_pos == (1, len('class '))
    assert name.end_pos == (1, len('class Foo'))
    assert name.value == 'Foo'

    name = get_sub('def foo(): pass').name
    assert name.start_pos == (1, len('def '))
    assert name.end_pos == (1, len('def foo'))
    assert name.value == 'foo'


def test_import_names(each_version):
    def get_import(source):
        return next(parse(source, version=each_version).iter_imports())

    imp = get_import('import math\n')
    names = imp.get_defined_names()
    assert len(names) == 1
    assert names[0].value == 'math'
    assert names[0].start_pos == (1, len('import '))
    assert names[0].end_pos == (1, len('import math'))

    assert imp.start_pos == (1, 0)
    assert imp.end_pos == (1, len('import math'))


def test_end_pos(each_version):
    s = dedent('''
               x = ['a', 'b', 'c']
               def func():
                   y = None
               ''')
    parser = parse(s, version=each_version)
    scope = next(parser.iter_funcdefs())
    assert scope.start_pos == (3, 0)
    assert scope.end_pos == (5, 0)


def test_carriage_return_statements(each_version):
    source = dedent('''
        foo = 'ns1!'

        # this is a namespace package
    ''')
    source = source.replace('\n', '\r\n')
    stmt = parse(source, version=each_version).children[0]
    assert '#' not in stmt.get_code()


def test_incomplete_list_comprehension(each_version):
    """ Shouldn't raise an error, same bug as #418. """
    # With the old parser this actually returned a statement. With the new
    # parser only valid statements generate one.
    children = parse('(1 for def', version=each_version).children
    assert [c.type for c in children] == \
        ['error_node', 'error_node', 'endmarker']


def test_newline_positions(each_version):
    endmarker = parse('a\n', version=each_version).children[-1]
    assert endmarker.end_pos == (2, 0)
    new_line = endmarker.get_previous_leaf()
    assert new_line.start_pos == (1, 1)
    assert new_line.end_pos == (2, 0)


def test_end_pos_error_correction(each_version):
    """
    Source code without ending newline are given one, because the Python
    grammar needs it. However, they are removed again. We still want the right
    end_pos, even if something breaks in the parser (error correction).
    """
    s = 'def x():\n .'
    m = parse(s, version=each_version)
    func = m.children[0]
    assert func.type == 'funcdef'
    assert func.end_pos == (2, 2)
    assert m.end_pos == (2, 2)


def test_param_splitting(each_version):
    """
    Jedi splits parameters into params, this is not what the grammar does,
    but Jedi does this to simplify argument parsing.
    """
    def check(src, result):
        m = parse(src, version=each_version)
        assert not list(m.iter_funcdefs())

    check('def x(a, (b, c)):\n pass', ['a'])
    check('def x((b, c)):\n pass', [])


def test_unicode_string():
    s = tree.String('bö', (0, 0))
    assert repr(s)  # Should not raise an Error!


def test_backslash_dos_style(each_version):
    assert parse('\\\r\n', version=each_version)


def test_started_lambda_stmt(each_version):
    m = parse('lambda a, b: a i', version=each_version)
    assert m.children[0].type == 'error_node'


@pytest.mark.parametrize('code', ['foo "', 'foo """\n', 'foo """\nbar'])
def test_open_string_literal(each_version, code):
    """
    Testing mostly if removing the last newline works.
    """
    lines = split_lines(code, keepends=True)
    end_pos = (len(lines), len(lines[-1]))
    module = parse(code, version=each_version)
    assert module.get_code() == code
    assert module.end_pos == end_pos == module.children[1].end_pos


def test_too_many_params():
    with pytest.raises(TypeError):
        parse('asdf', hello=3)


def test_dedent_at_end(each_version):
    code = dedent('''
        for foobar in [1]:
            foobar''')
    module = parse(code, version=each_version)
    assert module.get_code() == code
    suite = module.children[0].children[-1]
    foobar = suite.children[-1]
    assert foobar.type == 'name'


def test_no_error_nodes(each_version):
    def check(node):
        assert node.type not in ('error_leaf', 'error_node')

        try:
            children = node.children
        except AttributeError:
            pass
        else:
            for child in children:
                check(child)

    check(parse("if foo:\n bar", version=each_version))


def test_named_expression(works_ge_py38):
    works_ge_py38.parse("(a := 1, a + 1)")


def test_extended_rhs_annassign(works_ge_py38):
    works_ge_py38.parse("x: y = z,")
    works_ge_py38.parse("x: Tuple[int, ...] = z, *q, w")


@pytest.mark.parametrize(
    'param_code', [
        'a=1, /',
        'a, /',
        'a=1, /, b=3',
        'a, /, b',
        'a, /, b',
        'a, /, *, b',
        'a, /, **kwargs',
    ]
)
def test_positional_only_arguments(works_ge_py38, param_code):
    works_ge_py38.parse("def x(%s): pass" % param_code)


@pytest.mark.parametrize(
    'expression', [
        'a + a',
        'lambda x: x',
        'a := lambda x: x'
    ]
)
def test_decorator_expression(works_ge_py39, expression):
    works_ge_py39.parse("@%s\ndef x(): pass" % expression)


@pytest.mark.parametrize(
    'code', [
        'class Foo[T]: pass',
        'class Foo[T: str]: pass',
        'class Foo[T, U]: pass',
        'class Foo[T: str, U: int]: pass',
        'class Foo[T](Base): pass',
        'class Foo[T: str](Base, Mixin): pass',
        'class Foo[*Ts]: pass',
        'class Foo[**P]: pass',
    ]
)
def test_pep695_generic_class(works_ge_py312, code):
    works_ge_py312.parse(code)


@pytest.mark.parametrize(
    'code', [
        'def foo[T](x: T) -> T: pass',
        'def foo[T: int](x: T) -> T: pass',
        'def foo[T, U](x: T, y: U): pass',
        'def foo[*Ts](*args): pass',
        'def foo[**P](*args): pass',
    ]
)
def test_pep695_generic_function(works_ge_py312, code):
    works_ge_py312.parse(code)


def test_pep695_class_get_super_arglist(works_ge_py312):
    module = works_ge_py312.parse('class Foo[T](Bar, Baz): pass')
    if module is None:
        return
    classdef = module.children[0]
    arglist = classdef.get_super_arglist()
    assert arglist is not None
    assert 'Bar' in arglist.get_code()
    assert 'Baz' in arglist.get_code()


def test_pep695_class_no_bases(works_ge_py312):
    module = works_ge_py312.parse('class Foo[T]: pass')
    if module is None:
        return
    classdef = module.children[0]
    assert classdef.get_super_arglist() is None


@pytest.mark.parametrize(
    'code', [
        'class Foo[T = int]: pass',
        'class Foo[T: str = "default"]: pass',
        'class Foo[*Ts = tuple[int, ...]]: pass',
        'class Foo[**P = None]: pass',
        'def foo[T = int](x: T) -> T: pass',
    ]
)
def test_pep696_type_param_defaults(works_ge_py313, code):
    works_ge_py313.parse(code)


@pytest.mark.parametrize(
    'code', [
        'match x:\n case 1: pass\n',
        'match x:\n case 1:\n  pass\n case _:\n  pass\n',
        'match x,:\n case (1,): pass\n',
        'match x, *y:\n case a, *b: pass\n',
        'match (x := f()):\n case 1: pass\n',
        'match [x]:\n case [1]: pass\n',
        'match -x:\n case -1: pass\n',
        'match x:\n case None | True | False: pass\n',
        'match x:\n case "a" "b" | b"c": pass\n',
        'match x:\n case -1 | 1 | -1j | 1+2j | -1-2j: pass\n',
        'match x:\n case a: pass\n',
        'match x:\n case Color.RED | a.b.c: pass\n',
        'match x:\n case [] | () | {}: pass\n',
        'match x:\n case [a, b, *rest]: pass\n',
        'match x:\n case (a, *_, b): pass\n',
        'match x:\n case a, b: pass\n',
        'match x:\n case (a): pass\n',
        'match x:\n case {"k": v, 1: w, K.v: u, **rest}: pass\n',
        'match x:\n case {**rest,}: pass\n',
        'match x:\n case P(): pass\n',
        'match x:\n case P(1, a, x=2, y=b,): pass\n',
        'match x:\n case a.P(x=[1, {2: c}]): pass\n',
        'match x:\n case [a] | (a,) as b: pass\n',
        'match x:\n case (1 | 2) as a: pass\n',
        'match x:\n case a if a > 1: pass\n',
        'match x:\n case _ if x: pass\n case 1: pass\n',
        'match x:\n case y if y:\n  pass\n case _:\n  pass\n',
        'match x:\n case 1:\n  match y:\n   case 2: pass\n',
        'def f(x):\n match x:\n  case 1: return 1\n',
        'class C:\n match = 1\n match x:\n  case 1: pass\n',
        'if x:\n match x:\n  case 1: pass\nelse:\n pass\n',
        'for x in y:\n match x:\n  case 1: break\n  case 2: continue\n',
        'match x:\n case 1: pass\nmatch = 1\n',
        'match = 1\nmatch match:\n case 1: pass\n',
        'match x:\n case match: pass\n',
        'match x:\n case case: pass\n',
        'match x:\n case match.case: pass\n',
        'match x:\n case [match, case]: pass\n',
        'match x:\n case P(match=case): pass\n',
        'match x:\n case 1:\n  case = 1\n  match = 2\n  match(case)\n',
        'match x:\n # comment\n\n case 1: pass  # comment\n\n # other\n case 2: pass\n',
        'match (x,\n y):\n case (1,\n  2): pass\n',
        'match x: # comment\n case 1: pass',
    ]
)
def test_match_statement(works_ge_py310, code):
    works_ge_py310.parse(code)
    works_ge_py310.assert_no_error_in_passing(code)


@pytest.mark.parametrize(
    'code', [
        'match = 1\n',
        'case = 1\n',
        'match, case = 1, 2\n',
        'match: int = 1\n',
        'match.group(1)\n',
        'match[0] = 1\n',
        'match(x)\n',
        'match (x)\n',
        'match -x\n',
        'match = lambda case: case\n',
        'x = match\n',
        'x = {match: case}\n',
        're.match(x, case)\n',
        'print(match, case)\n',
        'def match(case): return case\n',
        'class match: case = 1\n',
        'lambda match, case: match\n',
        'import match\nfrom case import match as case\n',
        'case(x)\n',
        'case: int\n',
        'x = 1; match = 2; case = 3\n',
        'if x: match = 1\n',
    ]
)
def test_match_and_case_as_names(works_in_py, code):
    works_in_py.parse(code)
    works_in_py.assert_no_error_in_passing(code)


@pytest.mark.parametrize('version', ['3.8', '3.9'])
def test_match_statement_before_py310(version):
    code = 'match x:\n case 1: pass\n'
    with pytest.raises(ParserSyntaxError):
        parse(code, version=version, error_recovery=False)


def test_match_statement_tree():
    code = dedent('''\
        match x, y:
            case [1, *rest] if rest:
                pass
            case {"k": v} | P(a=v):
                pass

        match = 1
        ''')
    module = parse(code, version='3.10')
    assert module.get_code() == code
    match_stmt, assignment, _ = module.children
    assert match_stmt.type == 'match_stmt'
    keyword, subject, colon, newline, *cases = match_stmt.children
    assert (keyword.type, keyword.value) == ('keyword', 'match')
    assert subject.type == 'subject_expr'
    assert [case.type for case in cases] == ['case_block', 'case_block']
    assert [case.children[0].type for case in cases] == ['keyword', 'keyword']
    assert cases[0].children[2].type == 'guard'
    assert cases[1].children[1].type == 'or_pattern'
    assert all(child.type != 'operator' or child.value for child in match_stmt.children)
    assert assignment.children[0].children[0].type == 'name'


def test_match_statement_scopes():
    module = parse(dedent('''\
        match x:
            case 1:
                def f(): return 1
            case 2:
                class C: pass
                import os
        '''), version='3.10')
    assert [f.name.value for f in module.iter_funcdefs()] == ['f']
    assert [c.name.value for c in module.iter_classdefs()] == ['C']
    assert [i.get_code().strip() for i in module.iter_imports()] == ['import os']
    function, = module.iter_funcdefs()
    assert len(list(function.iter_return_stmts())) == 1


def test_match_statement_error_recovery():
    code = dedent('''\
        match x:
            case 1:
                pass
            foo bar
            case 2:
                pass
        match y
        match z:
        a = 1
        ''')
    module = parse(code, version='3.10')
    assert module.get_code() == code
