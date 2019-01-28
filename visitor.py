import lexing
import tree
import parsing

from functools import reduce
from copy import deepcopy as clone

import pickle

DEBUG = True

PROGRAM = None
with open('sample.txt', 'r') as f:
    PROGRAM = f.read()

if DEBUG:
    print('--- GIVEN PROGRAM ---\n' + PROGRAM + '\n-------- END --------')

stream = lexing.lex(PROGRAM)
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


class Variable(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

class Definition(object):
    def __init__(self, branch, table, taking, frozen):
        self.tree = branch
        self.frozen = frozen
        self.table = table
        self.args = taking
    def call(self):
        result = evaluate(self.tree)
        self.table.clean()
        return result

class SymbolTable(object):
    def __init__(self, scope, name = 'subscope'):
        self.scope = scope
        self.name = name
        self.local = {}
        self.args = []
        self.type = __class__
        self.frozen = False
        
    def push(self, symbol, value):
        if symbol in self.local.keys():
            raise Exception(
                'Symbol bindings are immutable, symbol: `%s' % symbol
                + "' cannot be mutated."
            )
        self.local[symbol] = value
    bind = push
    
    def declare(self, symbol):
        self.local[symbol] = None

    def declare_args(self, args):
        self.args = args

    def give_args(self, args):
        if len(self.args) != len(args):
            raise Exception('Not enough arguments supplied to call.')
        for i in range(len(args)):
            self.local[self.args[i]] = args[i]

    def clean(self):
        self.local = {}

    def freeze(self):
        self.frozen = True
        
    def __str__(self):
        return '<TABLE`{}` scope:{}{}>'.format(
            self.name,
            hex(self.scope),
            ['', ' [frozen]'][self.frozen]
        )

TABLES = [SymbolTable(0, 'main')]
OLD_TABLES = []

def lookup_table(scope):
    global TABLES
    return list(filter(lambda e: e.scope == scope, TABLES))[0]

def current_tables(current_scopes):
    global TABLES
    scopes = map(lambda table: table.scope, TABLES)
    tables = filter(lambda e: e.scope in current_scopes, TABLES)
    return list(tables)

# Searches with respect to scoping, starting with children.
def search_tables(current, ident):
    global TABLES
    subtree = None
    tables = OLD_TABLES + current_tables(current)
    if DEBUG: print("Current parent tables searching:", list(map(str, tables)))
    for table in tables[::-1]:  # Search backwards, from children towards parents
        if DEBUG: print("Looking at:", table)
        if DEBUG: print("With bound symbols:", list(table.local.keys()))
        if ident in list(table.local.keys()):
            if DEBUG: print("Matched symbol in table.\n" + str(table.local[ident]))
            subtree = table.local[ident]
            break
    if subtree is None:
        raise Exception(
            'Unbound symbol: `%s\'. ' % ident
            + 'Check if symbol is in scope, or has been defined')
    return subtree

search_symbol = search_tables
    

CURRENT_SCOPES = [0x0]  # Default scope is main scope.

def evaluate(node):
    global TABLES
    if DEBUG:
        print("Current scope: {}, i.e. '{}'".format(
            hex(CURRENT_SCOPES[-1]),
            lookup_table(CURRENT_SCOPES[-1]).name
        ))
        print("Frozen Tables: [{}]".format(', '.join(map(str, OLD_TABLES))))
    if node.type is tree.Numeric:
        return node.value
    if node.type is tree.Symbol:
        return search_tables(CURRENT_SCOPES, node.value)
    if node.type is tree.Call:
        if node.value.type is tree.Symbol:
            method = node.value.value
            
            if method == '+':
                result = sum(map(evaluate, node.operands))
                return result

            if method == '-':
                result = evaluate(node.operands[0]) - sum(map(evaluate, node.operands[1:]))
                return result

            if method == '*':
                result = reduce((lambda a, b: a * b), map(evaluate, node.operands))
                return result

            if method == '/':
                result = reduce((lambda a, b: a / b), map(evaluate, node.operands))
                return result
            
            if method == 'out':
                result = ' '.join(map(str, map(evaluate, node.operands)))
                if DEBUG:
                    print('[out] --- <STDOUT>: `' + result + "'")
                else:
                    print(result)
                return result
            if method == 'let':
                immediate_scope = CURRENT_SCOPES[-1]
                immediate_table = lookup_table(immediate_scope)
                for op in node.operands:
                    if DEBUG: print("Let is defining: ", op.value.value)
                    immediate_table.bind(op.value.value, evaluate(op.operands[0]))
                if DEBUG: print('After let, defined variables in current scope, are: ', lookup_table(CURRENT_SCOPES[-1]).local)
                
                return
            if method == 'lambda':
                table = SymbolTable(id(node), '_lambda')
                args = [node.operands[0].value] + node.operands[0].operands
                table.declare_args(list(map(lambda e: e.value, args)))
                TABLES.append(table)
                frozen = clone(current_tables(CURRENT_SCOPES + [id(node)]))
                [t.freeze() for t in frozen]
                return Definition(node.operands[1], table, args, frozen)
            
            if method == 'define':
                name = node.operands[0].value.value  # Method name
                if DEBUG: print("At time of definition of: '{}', scopes are: {}".format(name, list(map(str, current_tables(CURRENT_SCOPES)))))
                table = SymbolTable(id(node), name)
                TABLES.append(table)
                ops = list(map(lambda e: e.value, node.operands[0].operands))
                TABLES[-1].declare_args(ops)
                
                frozen = clone(current_tables(CURRENT_SCOPES + [id(node)]))
                definition = Definition(node.operands[1], table, ops, frozen)
                
                immediate_scope = CURRENT_SCOPES[-1]
                lookup_table(immediate_scope).bind(name, definition)
                
                return definition

            if method:
                result = execute_method(node)
                return result
            
            raise Exception('Unknown variable or method name `%s\'.' % method)
        else:  # Not a symbol being called...
            result = execute_method(node)
            return result
            
            
            
    raise Exception("Don't know what to do with %s" % str(node))
            

def execute_method(node):    
    definition = evaluate(node.value)

    args = list(map(lambda e: evaluate(e), node.operands))
    definition.table.give_args(args)   #ARGS NEED TO BE PICKED BEFORE SUPERSCOPE VARS
    for i in range(len(definition.frozen)):
        OLD_TABLES.append(definition.frozen[i])
    CURRENT_SCOPES.append(definition.table.scope)

    result = definition.call()
    CURRENT_SCOPES.pop()
    [OLD_TABLES.pop() for _ in range(len(definition.frozen))]
    definition.table.clean()
    return result

    

def visit(AST, pc=0):
    evaluate(AST[pc])
    
    if pc + 1 >= len(AST):
        return None
    return visit(AST, pc + 1)


if __name__ == '__main__':
    visit(AST)


if DEBUG: print('\n\n[!!] -- Set `DEBUG\' to `False\' in "visitor.py" to stop seeing this information.')
input('\n\nPress Enter to continue...')
