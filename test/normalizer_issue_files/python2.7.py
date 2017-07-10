import sys

print 1, 2 >> sys.stdout


foo = ur'This is not possible in Python 3.'

# This is actually printing a tuple.
#: E275:5
print(1, 2)
