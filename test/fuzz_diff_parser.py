"""
Usage:
  fuzz_diff_parser.py [--pdb|--ipdb] [-l] [-n=<nr>] [-x=<nr>] [--record=<file>] random [<path>]
  fuzz_diff_parser.py [--pdb|--ipdb] [-l] [--record=<file>] redo
  fuzz_diff_parser.py -h | --help

Options:
  -h --help              Show this screen
  --record=<file>        Exceptions are recorded in here [default: record.json]
  -n, --maxtries=<nr>    Maximum of random tries [default: 100]
  -x, --changes=<nr>     Amount of changes to be done to a file per try [default: 2]
  -l, --logging          Prints all the logs
  --pdb                  Launch pdb when error is raised
  --ipdb                 Launch ipdb when error is raised
"""

from __future__ import print_function
import logging
import sys
import os
import random

from docopt import docopt

import parso
from parso.utils import split_lines


def find_python_files_in_tree(file_path):
    if not os.path.isdir(file_path):
        yield file_path
        return
    for root, dirnames, filenames in os.walk(file_path):
        for name in filenames:
            if name.endswith('.py'):
                yield os.path.join(root, name)


def generate_line_modification(code, change_count):
    def random_line(include_end=False):
        return random.randint(0, len(lines) - (not include_end))

    lines = split_lines(code, keepends=True)
    for _ in range(change_count):
        if not lines:
            break

        if random.choice([False, True]):
            # Deletion
            del lines[random_line()]
        else:
            # Copy / Insertion
            lines.insert(
                # Make it possible to insert into the first and the last line
                random_line(include_end=True),
                # Use some line from the file. This doesn't feel totally
                # random, but for the diff parser it will feel like it.
                lines[random_line()]
            )
    return ''.join(lines)


def run(path, maxtries, debugger, change_count):
    grammar = parso.load_grammar()
    print("Checking %s" % path)
    with open(path) as f:
        code = f.read()
    try:
        for _ in range(maxtries):
            grammar.parse(code, diff_cache=True)
            code2 = generate_line_modification(code, change_count)
            grammar.parse(code2, diff_cache=True)
            print('.', end='')
            sys.stdout.flush()
        print()
    except Exception:
        print("Issue in file: %s" % path)
        if debugger:
            einfo = sys.exc_info()
            pdb = __import__(debugger)
            pdb.post_mortem(einfo[2])
        raise


def main(arguments):
    debugger = 'pdb' if arguments['--pdb'] else \
               'ipdb' if arguments['--ipdb'] else None
    record = arguments['--record']

    if arguments['--logging']:
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)

        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        root.addHandler(ch)

    parso.python.diff.DEBUG_DIFF_PARSER = True
    if arguments['redo']:
        raise NotImplementedError("This has not yet been implemented")
    elif arguments['random']:
        # A random file is used to do diff parser checks if no file is given.
        # This helps us to find errors in a lot of different files.
        file_path_generator = find_python_files_in_tree(arguments['<path>'] or '.')
        path = next(file_path_generator)
        run(path, int(arguments['--maxtries']), debugger, int(arguments['--changes']))
    else:
        raise NotImplementedError('Command is not implemented')


if __name__ == '__main__':
    arguments = docopt(__doc__)
    main(arguments)
