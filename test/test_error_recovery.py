from parso import parse


def test_with_stmt():
    module = parse('with x: f.\na')
    assert module.children[0].type == 'with_stmt'
    w, with_item, colon, f = module.children[0].children
    assert f.type == 'error_node'
    assert f.get_code(include_prefix=False) == 'f.'

    assert module.children[2].type == 'name'


def test_if_stmt():
    module = parse('if x: f.')# \nelse: g(
    if_stmt = module.children[0]
    assert if_stmt.type == 'if_stmt'
    if_, test, colon, f = if_stmt.children
    assert f.type == 'error_node'
    assert f.children[0].value == 'f'
    assert f.children[1].value == '.'
