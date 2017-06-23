if x > 2:
    #: E111:2
  print(x)
if True:
    #: E111:5
     print
    #: E116:6
      # 
    #: E116:2
  # what
    # Comment is fine
# Comment is also fine

if False:
print
print
# TODO this shouldn't actually be a 111 but an IndentationError. Please
#   correct.
#: E111:4
    print
mimetype = 'application/x-directory'
#: E116:5
     # 'httpd/unix-directory'
create_date = False

def start(self):
    if True: # Hello
        self.master.start() # Comment
        # try:
        #: E116:12
            # self.master.start()
        # except MasterExit:
        #: E116:12
            # self.shutdown()
        # finally:
        #: E116:12
            # sys.exit()
    # Dedent to the first level
    #: E116:6
      # error
# Dedent to the base level
#: E116:2
  # Also wrongly indented.
# Indent is correct.
def start(self):  # Correct comment
    if True:
        #: E115:0
#       try:
        #: E115:0
#           self.master.start()
        #: E115:0
#       except MasterExit:
        #: E115:0
#           self.shutdown()
        self.master.start() # comment
