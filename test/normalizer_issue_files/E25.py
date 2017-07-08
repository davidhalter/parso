#: E251:11 E251:13
def foo(bar = False):
    '''Test function with an error in declaration'''
    pass


#: E251:8
foo(bar= True)
#: E251:7
foo(bar =True)
#: E251:7 E251:9
foo(bar = True)
#: E251:13
y = bar(root= "sdasd")
parser.add_argument('--long-option',
                    #: E135+1:20
                    default=
                    "/rather/long/filesystem/path/here/blah/blah/blah")
parser.add_argument('--long-option',
                    default=
                        "/rather/long/filesystem")
# TODO this looks so stupid.
parser.add_argument('--long-option', default
                    ="/rather/long/filesystem/path/here/blah/blah/blah")
#: E251+2:7 E251+2:9
foo(True,
    baz=(1, 2),
    biz = 'foo'
    )
# Okay
foo(bar=(1 == 1))
foo(bar=(1 != 1))
foo(bar=(1 >= 1))
foo(bar=(1 <= 1))
(options, args) = parser.parse_args()
d[type(None)] = _deepcopy_atomic


# Annotated Function Definitions
# Okay
def munge(input: AnyStr, sep: AnyStr = None, limit=1000,
          extra: Union[str, dict] = None) -> AnyStr:
    pass


# Okay
async def add(a: int = 0, b: int = 0) -> int:
    return a + b


# Previously E251 four times
#: E221:5
async  def add(a: int = 0, b: int = 0) -> int:
    return a + b


#: E225:24 E225:26
def x(b: tuple = (1, 2))->int:
    return a + b


#: E252:11 E252:12 E231:8
def b(a:int=1):
    pass
