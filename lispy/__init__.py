from . import lexing
from . import tree
from . import parsing
from . import visitor

from . import err
from . import config as conf

import pickle, sys, os
import codecs

TEST_FILE = 'testing.lispy'

def run(file):
    PROGRAM_STRING = None
    with codecs.open(file, 'r', 'utf-8') as f:
        PROGRAM_STRING = f.read()

    if conf.DEBUG:
        print('--- GIVEN PROGRAM ---\n' + PROGRAM_STRING + '\n-------- END --------')

    stream = lexing.lex(PROGRAM_STRING, file)
    if conf.DEBUG:
        print("\n\nToken Stream:\n")
        print(stream)

    AST = parsing.parse(stream)
    if conf.DEBUG:
        print("\n\nAbstract Syntax Tree:\n")
        print(AST)

    dir = './serialised_trees'
    try:
        os.mkdir(dir)
    except:
        pass
    coded = '_'.join(file.split('/'))
    tree_file = '{}/{}'.format(
        dir,
        '.'.join(coded.split('.')[:-1]) + '_serialised.ast')
    with open(tree_file, 'w+', encoding='utf-8') as f:
        f.write('VISUALISED_ABSTRACT_SYNTAX_TREE\n')
        f.write(str(AST))
        f.write('\nSERIALISED_PICKLE_AST\n')
        f.write(str(pickle.dumps(AST)))
    visitor.walk(AST)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        run(sys.argv[1])
    else:
        run(TEST_FILE)

    if conf.DEBUG:
        print('\n\n[!!] -- Set `DEBUG\' to `False\' in "config.py" to stop seeing this information.')
        input('\n\nPress Enter to continue...')
