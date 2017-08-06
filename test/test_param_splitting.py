'''
To make the life of any analysis easier, we are generating Param objects
instead of simple parser objects.
'''

from textwrap import dedent

from parso import parse


def assert_params(param_string, version=None, **wanted_dct):
    source = dedent('''
    def x(%s):
        pass
    ''') % param_string

    module = parse(source, version=version)
    funcdef = next(module.iter_funcdefs())
    dct = dict((p.name.value, p.default and p.default.get_code())
               for p in funcdef.get_params())
    assert dct == wanted_dct
    assert module.get_code() == source


def test_split_params_with_separation_star():
    assert_params(u'x, y=1, *, z=3', x=None, y='1', z='3', version='3.5')
    assert_params(u'*, x', x=None, version='3.5')
    assert_params(u'*', version='3.5')


def test_split_params_with_stars():
    assert_params(u'x, *args', x=None, args=None)
    assert_params(u'**kwargs', kwargs=None)
    assert_params(u'*args, **kwargs', args=None, kwargs=None)
