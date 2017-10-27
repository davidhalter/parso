from parso import parse
from parso.python.tree import Scope, Module, Function, Class, Lambda

SAMPLE_CODE = """
def my_function():
    b = 1 + 2
    return b

class MyClass():
    attribute = 1
    def my_method():
        return lambda x: 3 * 3

"""


def test_empty_module_scope():
    """Test getting scope in an empty module"""

    tree = parse("")
    node = tree.get_leaf_for_position((1, 0), include_prefixes=True)
    scope = node.get_scope()

    assert isinstance(scope, Scope)
    assert isinstance(scope, Module)


def test_module_scope():
    """Test getting the scope of a function"""

    tree = parse(SAMPLE_CODE)
    node = tree.get_leaf_for_position((2, 1), include_prefixes=True)
    scope = node.get_scope().get_scope() #  function, then module

    assert isinstance(scope, Scope)
    assert isinstance(scope, Module)


def test_function_scope():
    """Test getting the scope of a leaf in a function"""
    tree = parse(SAMPLE_CODE)
    node = tree.get_leaf_for_position((2, 1), include_prefixes=True)
    scope = node.get_scope()

    assert isinstance(scope, Scope)
    assert isinstance(scope, Function)
    assert scope.name.value == "my_function"


def test_class_scope():
    """Test getting the scope of a leaf in a class"""

    tree = parse(SAMPLE_CODE)
    node = tree.get_leaf_for_position((7, 17), include_prefixes=True)
    scope = node.get_scope()

    assert isinstance(scope, Scope)
    assert isinstance(scope, Class)
    assert scope.name.value == "MyClass"


def test_method_scope():
    """Test getting the scope of a leaf in a class method"""

    tree = parse(SAMPLE_CODE)
    node = tree.get_leaf_for_position((9, 13), include_prefixes=True)
    scope = node.get_scope()

    assert isinstance(scope, Scope)
    assert isinstance(scope, Function)
    assert scope.name.value == "my_method"


def test_lambda_scope():
    """Test getting the scope of a leaf in a lambda"""

    tree = parse(SAMPLE_CODE)
    node = tree.get_leaf_for_position((9, 28), include_prefixes=True)
    scope = node.get_scope()

    assert isinstance(scope, Scope)
    assert isinstance(scope, Lambda)
