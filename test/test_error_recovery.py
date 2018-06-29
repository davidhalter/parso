from parso import parse


def test_with_stmt():
    module = parse('with x: f.\na')
    assert module.children[0].type == 'with_stmt'
    w, with_item, colon, f = module.children[0].children
    assert f.type == 'error_node'
    assert f.get_code(include_prefix=False) == 'f.'

    assert module.children[2].type == 'name'


def test_one_line_function(each_version):
    module = parse('def x(): f.', version=each_version)
    assert module.children[0].type == 'funcdef'
    def_, name, parameters, colon, f = module.children[0].children
    assert f.type == 'error_node'

    module = parse('def x(a:', version=each_version)
    func = module.children[0]
    assert func.type == 'error_node'
    if each_version.startswith('2'):
        assert func.children[-1].value == 'a'
    else:
        assert func.children[-1] == ':'


def test_if_else():
    module = parse('if x:\n f.\nelse:\n g(')
    if_stmt = module.children[0]
    if_, test, colon, suite1, else_, colon, suite2 = if_stmt.children
    f = suite1.children[1]
    assert f.type == 'error_node'
    assert f.children[0].value == 'f'
    assert f.children[1].value == '.'
    g = suite2.children[1]
    assert g.children[0].value == 'g'
    assert g.children[1].value == '('


def test_if_stmt():
    module = parse('if x: f.\nelse: g(')
    if_stmt = module.children[0]
    assert if_stmt.type == 'if_stmt'
    if_, test, colon, f = if_stmt.children
    assert f.type == 'error_node'
    assert f.children[0].value == 'f'
    assert f.children[1].value == '.'

    assert module.children[1].type == 'newline'
    assert module.children[1].value == '\n'
    assert module.children[2].type == 'error_leaf'
    assert module.children[2].value == 'else'
    assert module.children[3].type == 'error_leaf'
    assert module.children[3].value == ':'

    in_else_stmt = module.children[4]
    assert in_else_stmt.type == 'error_node'
    assert in_else_stmt.children[0].value == 'g'
    assert in_else_stmt.children[1].value == '('
