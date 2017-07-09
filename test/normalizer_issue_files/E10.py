for a in 'abc':
    for b in 'xyz':
        print a  # indented with 8 spaces
        # TODO currently not an error, because the indentation matches.
	print(b)  # indented with 1 tab
if True:
    #: E101:0
	pass

#: E122+1
change_2_log = \
"""Change 2 by slamb@testclient on 2006/04/13 21:46:23

	creation
"""

p4change = {
    2: change_2_log,
}


class TestP4Poller(unittest.TestCase):
    def setUp(self):
        self.setUpGetProcessOutput()
        return self.setUpChangeSource()

    def tearDown(self):
        pass


#
if True:
    #: E101:0 E101+1:0
	foo(1,
	    2)


def test_keys(self):
    """areas.json - All regions are accounted for."""
    expected = set([
        #: E101:0
	u'Norrbotten',
        #: E101:0
	u'V\xe4sterbotten',
    ])


if True:
    print("""
	tab at start of this line
""")
