import lexing
import tree
import parsing
import visitor

import pickle, sys

TEST_FILE = 'testing.lispy'
DEBUG = True

def run(file):
    PROGRAM_STRING = None
    with open(file, 'r') as f:
        PROGRAM_STRING = f.read()

    if DEBUG:
        print('--- GIVEN PROGRAM ---\n' + PROGRAM_STRING + '\n-------- END --------')

    stream = lexing.lex(PROGRAM_STRING, file)
    if DEBUG:
        print("\n\nToken Stream:\n")
        print(stream)
        
    AST = parsing.parse(stream)
    if DEBUG:
        print("\n\nAbstract Syntax Tree:\n")
        print(AST)
        with open('serialised-ast.txt', 'w', encoding='utf-8') as f:
            f.write('VISUALISED_ABSTRACT_SYNTAX_TREE\n')
            f.write(str(AST))
            f.write('\nSERIALISED_PICKLE_AST\n')
            f.write(str(pickle.dumps(AST)))
    visitor.visit(AST)

if __name__ == '__main__':
    run(TEST_FILE)

if DEBUG:
    print('\n\n[!!] -- Set `DEBUG\' to `False\' in "visitor.py" to stop seeing this information.')
input('\n\nPress Enter to continue...')
