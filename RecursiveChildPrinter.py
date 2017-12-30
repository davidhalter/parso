import parso

def print_all_nested_children(current_tab_depth, node):
    try:
        for child in node.children:
            print(current_tab_depth*"\t", "-", child)
            print_all_nested_children(current_tab_depth+1, child)
    except AttributeError:
        pass
        
def test():
    parsed_module = parso.parse('[x*2 for x in range(5)]', version="3.6")
    print_all_nested_children(1, parsed_module)
