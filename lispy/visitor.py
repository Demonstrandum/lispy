from . import lexing
from . import tree
from . import parsing

from . import err
from . import config as conf

from functools import reduce
from copy import copy as clone

import sys, os
import pickle

EX = None
CURRENT_LOCATION = None

class Atomise(object):
    def __init__(self, string):
        self.name = string
        self.hash = hash(string)
    def __eq__(self, other):
        return self.hash == other.hash

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
        self.mutables = []
        self.args = []
        self.type = __class__
        self.frozen = False

    def freeze(self):
        new = SymbolTable(self.scope, self.name)
        new.frozen = True
        new.local = clone(self.local)
        new.mutables = self.mutables
        new.args = self.args
        return new

    def push(self, symbol, value):
        global EX
        if symbol in self.local:
            if symbol not in self.mutables and symbol[0] != '$':
                s = (('Symbol bindings are immutable, symbol: `%s' % symbol)
                    + "' cannot be mutated.")
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

    def __str__(self):
        return '<TABLE`{}`:{}{}>'.format(
            self.name,
            hex(self.scope),
            ['', ' [frozen]'][self.frozen])

TABLES = [SymbolTable(0, '_main')]
FROZEN_TABLES = []
CALL_STACK = []

ATOMS = {':true': Atomise(':true'), ':false': Atomise(':false')}

def load_file(name):
    PROGRAM_STRING = None
    with open(name, 'r') as file:
        PROGRAM_STRING = file.read()
    stream = lexing.lex(PROGRAM_STRING, name)
    AST = parsing.parse(stream)
    visit(AST)

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

def symbol_declared(current, ident):
    global TABLES
    subtree = None
    tables = FROZEN_TABLES + current_tables(current) + CALL_STACK
    for table in tables[::-1]:  # Search backwards, from children towards parents
        if ident in list(table.local.keys()):
            return True
    return False

def is_node(node):
    return 'value' in dir(node)

def to_s(node):
    if node is None:
        return ''
    if not is_node(node):
        if type(node) is Definition:
            return '<definition`{}\' taking{}>'.format(
                node.table.name, list(map(to_s, node.args)))
        if type(node) is Atomise:
            return node.name
        return str(node)

    if node.type in [tree.Symbol, tree.Atom, tree.Numeric]:
        return str(node.value)

    if node.type == tree.Nil:
        return 'nil'

    if node.type == tree.Uneval:
        return '\'' + to_s(node.value)

    if node.type == tree.Call:
        operands = ' '.join(map(to_s, node.operands))
        operands = ['', ' '][len(operands) > 0] + operands
        return '(' + to_s(node.value) + operands + ')'

    return 'UNMAPED_DATATYPE'  # Really all datatypes should have their
                               #   own return value, but just in case
                               #   I forgot anythin, we'll return this.

# Function to check if node is a list...
def check_list(maybe_list, node):
    if not is_node(maybe_list):
        EX.throw(maybe_list.location,
            'The list to be indexed must be a list,\n'
            + 'i.e. it needs to be unevaluated,\n'
            + 'otherwise that list would become evaluated into\n'
            + 'something that is not a list anymore...')
    if maybe_list.value.type != tree.Call:
        EX.throw(maybe_list.location,
            'Argument for list is not a list,\n'
            + 'make sure that you are supplying an unevaluated\n'
            + 'list to the `index` macro...')

def name_node(node):
    base_case = (type(node) is str) or (type(node) is Atomise)
    if base_case: return base_case
    if type(node) is tree.Uneval and type(node.value) is tree.Symbol:
        return True
    return False

CURRENT_SCOPES = [0x0]  # Default scope is main scope (0x0).

def evaluate(node):
    global TABLES, CURRENT_SCOPES, FROZEN_TABLES, CALL_STACK
    global EX, CURRENT_LOCATION, ATOMS
    # All tables and scope/call stacks need to be
    # able to be modified by this method.

    if not is_node(node):
        return node  # Anything that isn't an AST node will simply
                     #   be retuned as itself, as that means it's already
                     #   an evaluated fundemental datatype attempting to be
                     #   evaluated with no reason. e.g. (eval 2)...

    CURRENT_LOCATION = node.location
    if conf.DEBUG:
        print("Current scope: {}, i.e. '{}'".format(
            hex(CURRENT_SCOPES[-1]),
            lookup_table(CURRENT_SCOPES[-1]).name))

        print("\nAll Scope Tables: [{}]".format(', '.join(map(str, TABLES))))
        print("\nCurrent Scopes:   [{}]".format(', '.join(map(str, CURRENT_SCOPES))))
        print("\nCall Tables:      [{}]".format(', '.join(map(str, CALL_STACK))))
        print("\nFrozen Tables:    [{}]".format(', '.join(map(str, FROZEN_TABLES))))

    if node.type is tree.Yield:
        return node  # Doesn't get evaluated per se.
    if node.type is tree.Nil:
        return node  # Doesn't get evaluated per se.
    if node.type is tree.Atom:
        if node.value in ATOMS:
            return ATOMS[node.value]
        ATOMS[node.value] = Atomise(node.value)
        return ATOMS[node.value]
    if node.type is tree.Numeric:
        return node.value
    if node.type is tree.Symbol:
        return search_tables(CURRENT_SCOPES, node.value)
    if node.type is tree.Uneval:
        return node  # Doesn't get evaluated per se.
    if node.type is tree.String:
        return node.value
    if node.type is tree.Call:
        if node.value is None:
            EX.throw(node.location,
                'Cannot make empty call. Evaluating an\n'+
                'empty list does not make sense.')
        if node.value.type is tree.Symbol:
            method = node.value.value
            if conf.DEBUG: print("Calling symbolic method: ", repr(method))

            if method == 'do':
                ret = tree.Nil(node.location)
                for op in node.operands:
                    e = evaluate(op)
                    if type(e) is tree.Yield:
                        ret = evaluate(e.value)
                        break

                return ret

            if method == 'require':
                files = list(map(evaluate, node.operands))

                i = 0
                for f in files:
                    if not name_node(f):
                        t = str(type(f))
                        if is_node(f):
                            if f.type is tree.Uneval:
                                t = 'Unevaluation of ' + f.value.name
                            else:
                                t = f.name
                        else:
                            if type(f) is int or type(f) is float:
                                t = 'Numeric'
                        EX.throw(node.operands[i].location,
                            'Can\'t interpret type `{}\' as a name for anything'.format(t))

                    file_name = None
                    if type(f) is Atomise:
                        file_name = f.name[1:]
                    elif type(f) is str:
                        file_name = f
                    elif type(f) is tree.Uneval:
                        file_name = f.value.value
                    if file_name is None:
                        EX.throw(node.operands[i].location,
                            'Was not able to deduce a filename from `require\n`'+
                            + 'argument supplied...')

                    curren_path = os.path.dirname(node.location['filename'])
                    file_name = curren_path + '/' + file_name
                    if not os.path.isfile(file_name):
                        file_name = file_name + '.lispy'
                        if not os.path.isfile(file_name):
                            EX.throw(node.operands[i].location,
                                'Cannot find file `{s}\' or `{s}.lispy\''.format(
                                    s=file_name
                                ))

                    # Start reading the actual file:
                    if conf.DEBUG: print("\n\nLOADING FILE: ", file_name)
                    load_file(file_name)
                    # Finished the walk...

                    i += 1
                return ATOMS[':true']

            if method == 'eval':
                if len(node.operands) > 1:
                    EX.throw(node.location, '`eval\' built-in macro takes exactly one argument')
                inside = evaluate(node.operands[0])
                if not is_node(inside):
                    return inside
                return evaluate(inside.value)

            if method == 'if':
                check = evaluate(node.operands[0])
                if check is ATOMS[':true'] and check:
                    return evaluate(node.operands[1])
                else:
                    if len(node.operands) > 2:
                        return evaluate(node.operands[2])
                return tree.Nil(node.location)

            if method == 'unless':
                check = evaluate(node.operands[0])
                if check is ATOMS[':false'] or (not check):
                    return evaluate(node.operands[1])
                else:
                    if len(node.operands) > 2:
                        return evaluate(node.operands[2])
                return tree.Nil(node.location)

            if method == 'list':
                # `list` is simply a way of writing '(1 2 3)
                #   as (list 1 2 3), the only difference is that all
                #   the arguments are evaluated at the time of the
                #   definition of the list, as oppsed to at access time.
                dlist = list(map(evaluate, node.operands))
                head = None
                tail = []
                if len(dlist) > 0:
                    head = dlist[0]
                    tail = dlist[1:]
                return tree.Uneval(
                    tree.Call(head, node.location, *tail),
                    node.location)

            if method == 'size':
                if len(node.operands) != 1:
                    EX.throw(node.operands[0].location,
                        '`size` built-in macro takes exactly one list argument')
                dlist = evaluate(node.operands[0])
                check_list(dlist, node)

                if dlist.value.value is None:
                    return 0
                return 1 + len(dlist.value.operands)

            if method == 'index':
                if len(node.operands) != 2:
                    EX.throw(node.location,
                        '`index` built-in macro takes exactly two arguments,\n'
                        + 'first needs to be a numeric integer index and\n'
                        + 'second an unevaluated list to be indexed.')
                index = evaluate(node.operands[0])
                data  = evaluate(node.operands[1])

                # We must be absolutely certian we have the correct type of
                #   arguments supplied to the index macro.
                if type(index) != int:
                    EX.throw(node.operands[0].location,
                        'Oridnal index number must be an integer!')
                check_list(data, node)
                # We are certain we have the correct datatypes supplied...

                dlist = [data.value.value] + data.value.operands
                if data.value.value is None:
                    EX.throw(node.operands[0].location,
                        'Cannot index empty list.')
                if index >= len(dlist):
                    EX.throw(node.operands[0].location,
                        'Index number out of range, tried to access\n'
                        + 'index number: {}, in a list only index from 0 to {}.'.format(
                            index, len(dlist) - 1
                        ))
                if index < 0:
                    # Negative indices will simply be looking at the list
                    #  from right to left, if we look at a negative index
                    #  that's got a magnitude greater than the magnitude of
                    #  the list, we will simply loop the back of the list again
                    #  by use of the modulus operator...
                    index = abs(index)
                    if index > len(dlist):
                        index %= len(dlist)
                    index = len(dlist) - index

                return evaluate(dlist[index])

            # push macro, for pushing to a list
            if method == 'push' or method == 'append':
                if len(node.operands) < 2:
                    EX.throw(node.location,
                        '`push` built-in macro needs at least\n'
                        + 'two arguments.')
                elems = list(map(evaluate, node.operands[:-1]))
                data = evaluate(node.operands[-1])
                # Check that data is indeed a list.
                check_list(data, node)

                if data.value.value is None:
                    data.value.value = elems[0]
                    data.value.operands += elems[1:]
                else:
                    data.value.operands += elems

                return data

            # Unshift adds items to the front of a list
            if method == 'unshift' or method == 'prepend':
                if len(node.operands) < 2:
                    EX.throw(node.location,
                        '`unshift` built-in macro needs at least\n'
                        + 'two arguments.')
                elems = list(map(evaluate, node.operands[:-1]))[::-1]
                data = evaluate(node.operands[-1])
                # Check that data is indeed a list.
                check_list(data, node)

                # We need to think about whether it's empty or not.
                if data.value.value is None:
                    data.value.value = elems[0]
                    data.value.operands = elems[1:] + data.value.operands
                else:
                    old_head = data.value.value
                    data.value.value = elems[0]
                    data.value.operands = elems[1:] + [old_head] + data.value.operands

                return data

            def concat():
                if len(node.operands) < 2:
                    EX.throw(node.value.location,
                        '`concat` must take two or more lists')
                dlists = list(map(evaluate, node.operands))
                for l in dlists:
                    check_list(l, node)

                concated = []
                for l in dlists:
                    if l.value.value is not None:
                        concated += [l.value.value] + l.value.operands
                here = node.location
                if len(concated) > 0:
                    return tree.Uneval(tree.Call(concated[0], here, *concated[1:]), here)
                else:
                    return tree.Uneval(tree.Call(None, here), here)

            if method == 'concat' or method == 'merge':
                return concat()

            if method == 'concat!' or method == 'merge!':
                concated = concat()
                first = evaluate(node.operands[0])

                first.value = concated.value
                return first

            def list_destruction(method):
                data = None
                amount = 1
                first_arg = evaluate(node.operands[0])
                if type(first_arg) is tree.Uneval:
                    data = first_arg
                else:
                    amount = first_arg
                    if type(amount) is not int:
                        EX.throw(node.operands[0].location,
                            'First argument supplied must be a list,\n'
                            + 'or a CARDINAL INTEGER, specifying how many\n'
                            + 'items are to be popped off the list.')
                    data = evaluate(node.operands[1])
                check_list(data, node)

                if data.value.value is None:
                    return data
                dlist = [data.value.value] + data.value.operands
                for _ in range(amount):
                    try:
                        method(dlist)
                    except:
                        break
                if len(dlist) == 0:
                    data.value.value = None
                    data.value.operands = []
                    return data
                data.value.value = dlist[0]
                data.value.operands = dlist[1:]
                return data

            if method == 'pop':
                return list_destruction(list.pop)

            if method == 'shift':
                return list_destruction(lambda l: l.pop(0))

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

            if method == '%':
                result = reduce(lambda a, b: a % b, map(evaluate, node.operands))
                return result

            if method == '=':
                result = reduce(lambda a, b: a == b, map(evaluate, node.operands))
                return [ATOMS[':false'], ATOMS[':true']][result]

            if method == '<':
                max = evaluate(node.operands[0])
                for op in node.operands[1:]:
                    after = evaluate(op)
                    if max >= after:
                        return ATOMS[':false']
                    max = after
                return ATOMS[':true']

            if method == '>':
                max = evaluate(node.operands[0])
                for op in node.operands[1:]:
                    after = evaluate(op)
                    if max <= after:
                        return ATOMS[':false']
                    max = after
                return ATOMS[':true']

            if method == '<=':
                max = evaluate(node.operands[0])
                for op in node.operands[1:]:
                    after = evaluate(op)
                    if max > after:
                        return ATOMS[':false']
                    max = after
                return ATOMS[':true']

            if method == '>=':
                max = evaluate(node.operands[0])
                for op in node.operands[1:]:
                    after = evaluate(op)
                    if max < after:
                        return ATOMS[':false']
                    max = after
                return ATOMS[':true']

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
                    if conf.DEBUG: print("let is defining: ", op.value.value)
                    if conf.DEBUG: print("while alredy: ", lookup_table(CURRENT_SCOPES[-1]).local, "... exist\n\n")
                    immediate_table.bind(op.value.value, evaluate(op.operands[0]))
                if conf.DEBUG: print('After let, defined variables in current scope, are: ', lookup_table(CURRENT_SCOPES[-1]).local)
                return

            if method == 'lambda':
                table = SymbolTable(id(node), '_lambda')
                args = [node.operands[0].value] + node.operands[0].operands
                table.declare_args(list(map(lambda e: e.value, args)))
                TABLES.append(table)
                frozen = current_tables(CURRENT_SCOPES + [id(node)])
                frozen = [t.freeze() for t in frozen]
                return Definition(node.operands[1], table, args, frozen)

            if method == 'define':
                name = node.operands[0].value.value  # Method name
                if conf.DEBUG: print("At time of definition of: '{}', scopes are: {}".format(name, list(map(str, current_tables(CURRENT_SCOPES)))))
                table = SymbolTable(id(node), name)
                TABLES.append(table)
                ops = list(map(lambda e: e.value, node.operands[0].operands))
                TABLES[-1].declare_args(ops)

                frozen = current_tables(CURRENT_SCOPES + [id(node)])
                frozen = [t.freeze() for t in frozen]
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
    if type(definition) is not Definition:
        EX.throw(node.value.location,
            'Cannot make call to to type of `{}\''.format(
                node.value.name
            ))

    args = list(map(lambda e: evaluate(e), node.operands))
    definition.table.give_args(args)
    for i in range(len(definition.frozen)):
        FROZEN_TABLES.append(definition.frozen[i])

    added = definition.table.scope not in CURRENT_SCOPES
    if added:
        CURRENT_SCOPES.append(definition.table.scope)
    CALL_STACK.append(definition.table.freeze())

    result = definition.call()
    if added:
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
    if not symbol_declared(CURRENT_SCOPES, '$PRELUDE_LOADING'):
        main_table = lookup_table(0x0)
        main_table.bind('$PRELUDE_LOADING', ATOMS[':true'])

        here = os.path.dirname(os.path.abspath(__file__))
        load_file(here + '/../prelude/prelude.lispy')

        main_table.bind('$PRELUDE_LOADED', ATOMS[':true'])

        if conf.DEBUG: print('\n\nAUTOMATICALLY LOADED PRELUDE\n\n')

    return visit(AST)
