import lexing
import tree
import parsing
import visitor

import err
import config as conf

import pickle, sys

TEST_FILE = 'testing.lispy'

def run(file):
    PROGRAM_STRING = None
    with open(file, 'r') as f:
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
        with open('serialised-ast.txt', 'w', encoding='utf-8') as f:
            f.write('VISUALISED_ABSTRACT_SYNTAX_TREE\n')
            f.write(str(AST))
            f.write('\nSERIALISED_PICKLE_AST\n')
            f.write(str(pickle.dumps(AST)))
    visitor.walk(AST)

if __name__ == '__main__':
    run(TEST_FILE)

if conf.DEBUG:
    print('\n\n[!!] -- Set `DEBUG\' to `False\' in "config.py" to stop seeing this information.')
    input('\n\nPress Enter to continue...')
