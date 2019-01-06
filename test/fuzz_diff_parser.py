"""
A script to find bugs in the diff parser.

Usage:
  fuzz_diff_parser.py [--pdb|--ipdb] [-l] [-n=<nr>] [-x=<nr>] random [<path>]
  fuzz_diff_parser.py [--pdb|--ipdb] [-l] redo [-o=<nr>] [-p]
  fuzz_diff_parser.py -h | --help

Options:
  -h --help              Show this screen
  -n, --maxtries=<nr>    Maximum of random tries [default: 100]
  -x, --changes=<nr>     Amount of changes to be done to a file per try [default: 2]
  -l, --logging          Prints all the logs
  -o, --only-last=<nr>   Only runs the last n iterations; Defaults to running all
  -p, --print-diffs      Print all test diffs
  --pdb                  Launch pdb when error is raised
  --ipdb                 Launch ipdb when error is raised
"""

from __future__ import print_function
import logging
import sys
import os
import random
import pickle
import difflib

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


class LineDeletion:
    def __init__(self, line_nr):
        self.line_nr = line_nr

    def apply(self, code_lines):
        del code_lines[self.line_nr]


class LineCopy:
    def __init__(self, copy_line, insertion_line):
        self._copy_line = copy_line
        self._insertion_line = insertion_line

    def apply(self, code_lines):
        code_lines.insert(
            self._insertion_line,
            # Use some line from the file. This doesn't feel totally
            # random, but for the diff parser it will feel like it.
            code_lines[self._copy_line]
        )


class FileModification:
    @classmethod
    def generate(cls, code_lines, change_count):
        return cls(list(cls._generate_line_modifications(code_lines, change_count)))

    @staticmethod
    def _generate_line_modifications(lines, change_count):
        def random_line(include_end=False):
            return random.randint(0, len(lines) - (not include_end))

        lines = list(lines)
        for _ in range(change_count):
            if not lines:
                break

            if random.choice([False, True]):
                l = LineDeletion(random_line())
            else:
                # Copy / Insertion
                # Make it possible to insert into the first and the last line
                l = LineCopy(random_line(), random_line(include_end=True))
            l.apply(lines)
            yield l

    def __init__(self, modification_list):
        self._modification_list = modification_list

    def _apply(self, code_lines):
        changed_lines = list(code_lines)
        for modification in self._modification_list:
            modification.apply(changed_lines)
        return changed_lines

    def run(self, grammar, code_lines, print_diff):
        code = ''.join(code_lines)
        modified_lines = self._apply(code_lines)
        modified_code = ''.join(modified_lines)

        if print_diff:
            print(''.join(
                difflib.unified_diff(code_lines, modified_lines)
            ))

        grammar.parse(code, diff_cache=True)
        grammar.parse(modified_code, diff_cache=True)
        # Also check if it's possible to "revert" the changes.
        grammar.parse(code, diff_cache=True)


class FileTests:
    def __init__(self, file_path, test_count, change_count):
        self._path = file_path
        with open(file_path) as f:
            code = f.read()
        self._code_lines = split_lines(code, keepends=True)
        self._test_count = test_count
        self._change_count = change_count

        with open(file_path) as f:
            code = f.read()
        self._file_modifications = []

    def _run(self, grammar, file_modifications, debugger, print_diffs=False):
        try:
            print("Checking %s" % self._path)
            for i, fm in enumerate(file_modifications, 1):
                fm.run(grammar, self._code_lines, print_diff=print_diffs)
                print('.', end='')
                if i % 1000 == 0:
                    print('\n%s tries' % i)
                sys.stdout.flush()
            print()
        except Exception:
            print("Issue in file: %s" % self._path)
            raise
            if debugger:
                einfo = sys.exc_info()
                pdb = __import__(debugger)
                pdb.post_mortem(einfo[2])
            raise

    def redo(self, grammar, debugger, only_last, print_diffs):
        mods = self._file_modifications
        if only_last is not None:
            mods = mods[-only_last:]
        self._run(grammar, mods, debugger, print_diffs=print_diffs)

    def run(self, grammar, debugger):
        def iterate():
            for _ in range(self._test_count):
                fm = FileModification.generate(self._code_lines, self._change_count)
                self._file_modifications.append(fm)
                yield fm

        self._run(grammar, iterate(), debugger)


def main(arguments):
    debugger = 'pdb' if arguments['--pdb'] else \
               'ipdb' if arguments['--ipdb'] else None
    redo_file = os.path.join(os.path.dirname(__file__), 'fuzz-redo.pickle')

    if arguments['--logging']:
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)

        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        root.addHandler(ch)

    grammar = parso.load_grammar()
    parso.python.diff.DEBUG_DIFF_PARSER = True
    if arguments['redo']:
        with open(redo_file, 'rb') as f:
            file_tests_obj = pickle.load(f)
        only_last = arguments['--only-last'] and int(arguments['--only-last'])
        file_tests_obj.redo(
            grammar,
            debugger,
            only_last=only_last,
            print_diffs=arguments['--print-diffs']
        )
    elif arguments['random']:
        # A random file is used to do diff parser checks if no file is given.
        # This helps us to find errors in a lot of different files.
        file_path_generator = find_python_files_in_tree(arguments['<path>'] or '.')
        path = next(file_path_generator)
        file_tests_obj = FileTests(
            path, int(arguments['--maxtries']), int(arguments['--changes'])
        )
        try:
            file_tests_obj.run(grammar, debugger)
        except Exception:
            with open(redo_file, 'wb') as f:
                pickle.dump(file_tests_obj, f)
            raise
    else:
        raise NotImplementedError('Command is not implemented')


if __name__ == '__main__':
    arguments = docopt(__doc__)
    main(arguments)
