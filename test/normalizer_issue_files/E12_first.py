print "E121", (
    #: E121:2
  "dent")
print "E122", (
    #: E121:0
"dent")
my_list = [
    1, 2, 3,
    4, 5, 6,
    #: E123
    ]
print "E124", ("visual",
               "indent_two"
               #: E124:14
              )
print "E124", ("visual",
               "indent_five"
               #: E124:0
)
a = (123,
     #: E124:0
)
#: E129+1:4
if (row < 0 or self.moduleCount <= row or
    col < 0 or self.moduleCount <= col):
    raise Exception("%s,%s - %s" % (row, col, self.moduleCount))

print "E126", (
    #: E126:12
            "dent")
print "E126", (
    #: E126:8
        "dent")
print "E127", ("over-",
               #: E127:18
                  "over-indent")
print "E128", ("visual",
               #: E128:4
    "hanging")
print "E128", ("under-",
               #: E128:14
              "under-indent")


my_list = [
    1, 2, 3,
    4, 5, 6,
    #: E123:5
     ]
result = {
    #: E121:3
   'key1': 'value',
    #: E121:3
   'key2': 'value',
}
rv.update(dict.fromkeys((
              'qualif_nr', 'reasonComment_en', 'reasonComment_fr',
              'reasonComment_de', 'reasonComment_it'),
          #: E128
          '?'),
          "foo")

#: E126+1:10 E126+2:10
abricot = 3 + \
          4 + \
          5 + 6
print "hello", (

    "there",
    #: E131:5
     # "john",
    "dude")
part = set_mimetype((
    a.get('mime_type', 'text')),
                    'default')
part = set_mimetype((
    a.get('mime_type', 'text')),
    #: E127:21
                     'default')
