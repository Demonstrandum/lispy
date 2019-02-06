from . import lexing
from . import tree
from . import parsing

from . import err
from . import config as conf

from functools import reduce
from copy import deepcopy as clone

import sys
import pickle

EX = None
CURRENT_LOCATION = None

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
        global EX
        if symbol in self.local.keys():
            s = 'Symbol bindings are immutable, symbol: `%s' % symbol
            + "' cannot be mutated."
            EX.throw(CURRENT_LOCATION, s)
        self.local[symbol] = value
    bind = push

    def declare(self, symbol):
        self.local[symbol] = None

    def declare_args(self, args):
        self.args = args

    def give_args(self, args):
        global EX
        if len(self.args) != len(args):
            s = 'Wrong number of arguments to `{}\',\nexpected: {}, got {}.'.format(
                self.name, len(self.args), len(args))
            EX.throw(CURRENT_LOCATION, s)
        for i in range(len(args)):
            self.local[self.args[i]] = args[i]

    def clean(self):
        self.local = {}

    def freeze(self):
        self.frozen = True

    def __str__(self):
        return '<TABLE`{}`:{}{}>'.format(
            self.name,
            hex(self.scope),
            ['', ' [frozen]'][self.frozen])

TABLES = [SymbolTable(0, 'main')]
FROZEN_TABLES = []
CALL_STACK = []

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
    tables = FROZEN_TABLES + current_tables(current) + CALL_STACK
    if conf.DEBUG:
        print("\n\nSearching current scopes for symbol: ", ident)
        print("Current parent tables searching:", list(map(str, tables)))
    for table in tables[::-1]:  # Search backwards, from children towards parents
        if conf.DEBUG: print("Looking at:", table)
        if conf.DEBUG: print("With bound symbols:", list(table.local.keys()))
        if ident in list(table.local.keys()):
            if conf.DEBUG: print("Matched symbol in table.\n" + str(table.local[ident]))
            subtree = table.local[ident]
            break
    if subtree is None:
        s = ('Unbound symbol: `{}\', in scope: {}.\n'
            + 'Check if symbol is in scope, or has been defined').format(
            ident, current_tables(current)[-1]
        )
        EX.throw(CURRENT_LOCATION, s)
    if conf.DEBUG: print("[!!] - Finished symbol search.\n\n")
    return subtree

search_symbol = search_tables

def is_node(node):
    return 'value' in dir(node)

def to_s(node):
    if not is_node(node):
        return str(node)

    if node.type in [tree.Symbol, tree.Atom, tree.Numeric]:
        return str(node.value)

    if node.type == tree.Nil:
        return 'Nil'

    if node.type == tree.Uneval:
        return '\'' + to_s(node.value)

    if node.type == tree.Call:
        operands = ' '.join(map(to_s, node.operands))
        operands = ['', ' '][len(operands) > 0] + operands
        return '(' + to_s(node.value) + operands + ')'

    return 'UNMAPED_DATATYPE'

CURRENT_SCOPES = [0x0]  # Default scope is main scope.

def evaluate(node):
    global TABLES, CURRENT_SCOPES, FROZEN_TABLES, CALL_STACK
    global EX, CURRENT_LOCATION

    if not is_node(node):
        return node

    CURRENT_LOCATION = node.location
    if conf.DEBUG:
        print("Current scope: {}, i.e. '{}'".format(
            hex(CURRENT_SCOPES[-1]),
            lookup_table(CURRENT_SCOPES[-1]).name))

        print("All Scope Tables: [{}]".format(', '.join(map(str, TABLES))))
        print("Frozen Tables: [{}]".format(', '.join(map(str, FROZEN_TABLES))))

    if node.type is tree.Nil:
        return None
    if node.type is tree.Numeric:
        return node.value
    if node.type is tree.Symbol:
        return search_tables(CURRENT_SCOPES, node.value)
    if node.type is tree.Uneval:
        return node
    if node.type is tree.Call:
        if node.value.type is tree.Symbol:
            method = node.value.value
            if conf.DEBUG: print("Calling symbolic method: ", repr(method))
            if method == 'if':
                if evaluate(node.operands[0]):
                    return evaluate(node.operands[1])
                else:
                    if len(node.operands) > 2:
                        return evaluate(node.operands[2])
                return None

            if method == 'unless':
                if not evaluate(node.operands[0]):
                    return evaluate(node.operands[1])
                else:
                    if len(node.operands) > 2:
                        return evaluate(node.operands[2])
                return None

            if method == 'eval':
                if len(node.operands) > 1:
                    EX.throw(node.location, 'Internal function `eval\' takes exactly one argument')
                inside = evaluate(node.operands[0])
                if not is_node(inside):
                    return inside
                return evaluate(inside.value)

            if method == '+':
                result = sum(map(evaluate, node.operands))
                return result

            if method == '-':
                if len(node.operands) == 1:
                    return -evaluate(node.operands[0])
                result = evaluate(node.operands[0]) - sum(map(evaluate, node.operands[1:]))
                return result

            if method == '*':
                result = reduce(lambda a, b: a * b, map(evaluate, node.operands))
                return result

            if method == '/':
                result = reduce(lambda a, b: a / b, map(evaluate, node.operands))
                return result

            if method == '=':
                result = reduce(lambda a, b: a == b, map(evaluate, node.operands))
                return result

            if method == '<':
                max = evaluate(node.operands[0])
                for op in node.operands[1:]:
                    after = evaluate(op)
                    if max >= after:
                        return False
                    max = after
                return True

            if method == '>':
                max = evaluate(node.operands[0])
                for op in node.operands[1:]:
                    after = evaluate(op)
                    if max <= after:
                        return False
                    max = after
                return True

            if method == '<=':
                max = evaluate(node.operands[0])
                for op in node.operands[1:]:
                    after = evaluate(op)
                    if max > after:
                        return False
                    max = after
                return True

            if method == '>=':
                max = evaluate(node.operands[0])
                for op in node.operands[1:]:
                    after = evaluate(op)
                    if max < after:
                        return False
                    max = after
                return True

            if method == 'string':
                compositon = lambda x: to_s(evaluate(x))
                return ' '.join(map(compositon, node.operands))

            if method == 'out':
                compositon = lambda x: to_s(evaluate(x))
                result = ' '.join(map(str, map(compositon, node.operands)))
                if conf.DEBUG:
                    print('[out] --- <STDOUT>: `' + result + "'")
                else:
                    sys.stdout.write(result)
                return result

            if method == 'puts':
                compositon = lambda x: to_s(evaluate(x))
                result = '\n'.join(map(str, map(compositon, node.operands)))
                if conf.DEBUG:
                    print('[puts] --- <STDOUT>: `' + result + "'")
                else:
                    print(result)
                return result

            if method == 'let':
                immediate_scope = CURRENT_SCOPES[-1]
                immediate_table = lookup_table(immediate_scope)
                for op in node.operands:
                    if conf.DEBUG: print("Let is defining: ", op.value.value)
                    immediate_table.bind(op.value.value, evaluate(op.operands[0]))
                if conf.DEBUG: print('After let, defined variables in current scope, are: ', lookup_table(CURRENT_SCOPES[-1]).local)
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
                if conf.DEBUG: print("At time of definition of: '{}', scopes are: {}".format(name, list(map(str, current_tables(CURRENT_SCOPES)))))
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

            raise Exception('Unknown variable or method name, this is a bug `%s\'.' % method)
        else:  # Not a symbol being called...
            result = execute_method(node)
            return result



    raise Exception("Don't know what to do with %s, this is a bug" % str(node))


def execute_method(node):
    definition = evaluate(node.value)

    args = list(map(lambda e: evaluate(e), node.operands))
    definition.table.give_args(args)
    for i in range(len(definition.frozen)):
        FROZEN_TABLES.append(definition.frozen[i])
    CURRENT_SCOPES.append(definition.table.scope)
    CALL_STACK.append(clone(definition.table))

    result = definition.call()
    CURRENT_SCOPES.pop()
    [FROZEN_TABLES.pop() for _ in range(len(definition.frozen))]
    CALL_STACK.pop()
    definition.table.clean()
    return result


# All evaluation starts here:
def visit(AST, pc=0):
    if pc >= len(AST):
        return 0

    evaluate(AST[pc])
    return visit(AST, pc + 1)

def walk(AST):
    global EX
    EX = err.Thrower(err.EXEC, AST.file)
    return visit(AST)
