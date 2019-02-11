from . import lexing
from . import tree
from . import parsing

from . import err
from . import config as conf

from functools import reduce
from copy import copy as clone
from types import FunctionType as function

import sys, os
import pickle

EX = None
CURRENT_LOCATION = {'line': 1, 'column': 1, 'filename': '.'}

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
    def __init__(self, scope, name = 'subscope', block=None):
        self.scope = scope
        self.name = name
        self.local = {}
        self.mutables = []
        self.args = []
        self.type = __class__
        self.block = block
        self.frozen = False

    def freeze(self):
        new = SymbolTable(self.scope, self.name, self.block)
        new.frozen = True
        new.local = clone(self.local)
        new.mutables = self.mutables
        new.args = self.args
        return new

    def push(self, symbol, value, mutable=False):
        global EX
        if symbol in self.local:
            if not (mutable or symbol in self.mutables or symbol[0] == '$'):
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

TABLES = [SymbolTable(0, '_main', None)]
FROZEN_TABLES = []
CALL_STACK = []

ATOMS = {':true': Atomise(':true'), ':false': Atomise(':false')}

def unity(l):
    l = list(l)
    return all(e == l[0] for e in l)

def load_file(name):
    PROGRAM_STRING = None
    with open(name, 'r') as file:
        PROGRAM_STRING = file.read()
    stream = lexing.lex(PROGRAM_STRING, name)
    AST = parsing.parse(stream)
    visit(AST)

def lookup_table(scope):
    global TABLES, FROZEN_TABLES, CALL_STACK
    all_tables = FROZEN_TABLES + TABLES + CALL_STACK
    return list(filter(lambda e: e.scope == scope, all_tables))[-1]

def current_tables(current_scopes):
    global TABLES, FROZEN_TABLES, CALL_STACK
    scopes = map(lambda table: table.scope, TABLES)
    tables = filter(lambda e: e.scope in current_scopes, TABLES)
    return FROZEN_TABLES + list(tables) + CALL_STACK

def where_symbol(current_scopes, sym):
    tables = current_tables(current_scopes)
    for t in tables[::-1]:
        if sym in t.local:
            return t
    EX.throw(CURRENT_LOCATION,
        'Symbol `{}\' does not exist in the current scope.'.format(
            sym))

# Searches with respect to scoping, starting with children.
def search_tables(current, ident):
    global TABLES, FROZEN_TABLES, CALL_STACK
    subtree = None
    tables = current_tables(current)
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

def to_type(node):
    if node is None:
        return 'Empty'
    if type(node) is function:
        return 'Macro'
    if type(node) is Definition:
        return 'Function'
    if type(node) is Atomise:
        return 'Atom'
    if isinstance(node, (str, tree.String)):
        return 'String'
    if isinstance(node, (int, float, tree.Numeric)):
        return 'Numeric'
    if type(node) is tree.Symbol:
        return 'Symbol'
    if type(node) is tree.Nil:
        return 'Nil'
    if type(node) is tree.Uneval:
        return 'Uneval'
    if type(node) is tree.Call:
        return 'Call'

def to_s(node):
    if node is None:
        return ''

    if type(node) is function:
        return '<macro`{}\'>'.format(
            node.__name__)

    if type(node) is Definition:
        return '<definition`{}\' taking{}>'.format(
            node.table.name, list(map(to_s, node.args)))

    if type(node) is Atomise:
        return node.name

    if not is_node(node):
        return str(node)

    if node.type in [tree.Symbol, tree.Atom, tree.Numeric]:
        return str(node.value)

    if node.type == tree.Nil:
        return 'nil'

    if node.type == tree.Uneval:
        return '\'' + to_s(node.value)

    if node.type == tree.String:
        return '"{}"'.format(node.value)

    if node.type == tree.Call:
        operands = ' '.join(map(to_s, node.operands))
        operands = ['', ' '][len(operands) > 0] + operands
        return '(' + to_s(node.value) + operands + ')'

    return 'UNMAPED_DATATYPE[{}]'.format(node.name)
                               # Really all datatypes should have their
                               #   own return value, but just in case
                               #   I forgot anythin, we'll return this.

# Function to check if node is a list...
def check_list(maybe_list, node):
    if not is_node(maybe_list):
        if type(maybe_list) is str:
            return tree.String
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
    return tree.Uneval

def name_node(node):
    base_case = (type(node) is str) or (type(node) is Atomise)
    if base_case: return base_case
    if type(node) is tree.Uneval and type(node.value) is tree.Symbol:
        return True
    return False

CURRENT_SCOPES = [0x0]  # Default scope is main scope (0x0).

def _do_macro(node):
    ret = tree.Nil(node.location)
    for op in node.operands:
        e = evaluate(op)
        if type(e) is tree.Yield:
            return evaluate(e.value)
        ret = e
    return ret

def _yield_macro(node):
    return node

def _require_macro(node):
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


def _eval_macro(node):
    if len(node.operands) > 1:
        EX.throw(node.location, '`eval\' built-in macro takes exactly one argument')
    inside = evaluate(node.operands[0])
    if not is_node(inside):
        return inside
    return evaluate(inside.value)


def _if_macro(node):
    check = evaluate(node.operands[0])
    if check is ATOMS[':true'] and check:
        return evaluate(node.operands[1])
    else:
        if len(node.operands) > 2:
            return evaluate(node.operands[2])
    return tree.Nil(node.location)


def _unless_macro(node):
    check = evaluate(node.operands[0])
    if check is ATOMS[':false'] or (not check):
        return evaluate(node.operands[1])
    else:
        if len(node.operands) > 2:
            return evaluate(node.operands[2])
    return tree.Nil(node.location)


def _list_macro(node):
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

def _size_macro(node):
    if len(node.operands) != 1:
        EX.throw(node.operands[0].location,
            '`size` built-in macro takes exactly one list argument')
    dlist = evaluate(node.operands[0])
    check_list(dlist, node)

    if dlist.value.value is None:
        return 0
    return 1 + len(dlist.value.operands)

def _index_macro(node):
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

def _push_macro(node):
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

def _unshift_macro(node):
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

# Helper method
def concat(node):
    if len(node.operands) < 2:
        EX.throw(node.value.location,
            '`concat` must take two or more lists (x)or strings')
    dlists = list(map(evaluate, node.operands))
    types = []
    for l in dlists:
        types.append(check_list(l, node))

    if not unity(types):
        EX.throw(node.value.location,
            'Tried concating two or more items of unequal type!\n'
            + 'All arguments supplied need to be of the same type.')

    if types[0] is tree.String:
        return ''.join(dlists)

    # Otherwise it's an unevaluated list
    concated = []
    for l in dlists:
        if l.value.value is not None:
            concated += [l.value.value] + l.value.operands
    here = node.location
    if len(concated) > 0:
        return tree.Uneval(tree.Call(concated[0], here, *concated[1:]), here)
    else:
        return tree.Uneval(tree.Call(None, here), here)



def _concat_macro(node):
    return concat(node)

def _concat_des_macro(node):
    concated = concat(node)
    first = evaluate(node.operands[0])

    if type(first) is str:
        tab = None
        if node.operands[0].type is tree.Symbol:
            tab = where_symbol(CURRENT_SCOPES, node.operands[0].value)
        tab.bind(node.operands[0].value, concated, mutable=True)
    else:
        first.value = concated.value
    return concated

# Helper method
def list_destruction(method, node):
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


def _pop_macro(node):
    return list_destruction(list.pop, node)

def _shift_macro(node):
    return list_destruction(lambda l: l.pop(0), node)

def _composition_macro(node):
    funcs = list(map(evaluate, node.operands))[::-1]
    def _composition(n, funcs=funcs):
        args = list(map(evaluate, n.operands))
        ret = None
        for f in funcs:
            if type(f) is function:
                fake_call = tree.Call(tree.Symbol(f.__name__, n.location), n.location, *args)
                ret = f(fake_call)
            else:
                ret = execute_method(f, args)

            args = [ret]
        return ret
    return _composition


def _add_macro(node):
    args = list(map(evaluate, node.operands))
    if not unity(map(to_type, args)):
        EX.throw(node.value.location,
            '`+` built-in macro requires all arguments to be of the same type.')
    if type(args[0]) is str:
        return ''.join(args)
    elif isinstance(args[0], (int, float)):
        return sum(args)
    EX.throw(node.value.location,
        'Unrecognised argument type {} for `+` macro'.format(
            to_type(args[0])))

def all_numerics(ops):
    for op in ops:
        if to_type(evaluate(op)) != 'Numeric':
            EX.throw(op.location,
                'All arguments to this macro must\n'
                + 'be of type `Numeric`!')

def _sub_macro(node):
    all_numerics(node.operands)
    if len(node.operands) == 1:
        return -evaluate(node.operands[0])
    result = evaluate(node.operands[0]) - sum(map(evaluate, node.operands[1:]))
    return result

def _mul_macro(node):
    all_numerics(node.operands)
    r = reduce(lambda a, b: a * b, map(evaluate, node.operands))
    return r

def _div_macro(node):
    all_numerics(node.operands)
    r = reduce(lambda a, b: a / b, map(evaluate, node.operands))
    return r

def _mod_macro(node):
    all_numerics(node.operands)
    r = reduce(lambda a, b: a % b, map(evaluate, node.operands))
    return r

def _eq_macro(node):
    r = unity(map(evaluate, node.operands))
    return [ATOMS[':false'], ATOMS[':true']][r]

def truthy(node):
    if type(node) is Atomise and node == ATOMS[':false']:
        return False
    return not not node

def internal_bool(bool):
    return [ATOMS[':false'], ATOMS[':true']][bool]

def _nq_macro(node):
    return [ATOMS[':true'], ATOMS[':false']][_eq_macro(node) == ATOMS[':true']]

def _ne_macro(node):
    op = evaluate(node.operands[0])
    return [ATOMS[':true'], ATOMS[':false']][truthy(op)]

def _and_macro(node):
    comp = lambda e: truthy(evaluate(e))
    truths = list(map(comp, node.operands))
    return internal_bool(all(truths))

def _or_macro(node):
    comp = lambda e: truthy(evaluate(e))
    truths = list(map(comp, node.operands))
    return internal_bool(any(truths))

def _xor_macro(node):
    comp = lambda e: truthy(evaluate(e))
    truths = list(map(comp, node.operands))
    if len(truths) != 2:
        EX.throw(node.value.location,
            '`^^` (XOR) built-in macro takes exactly two arguments.')
    return internal_bool(any(truths) and not all(truths))

def _lt_macro(node):
    all_numerics(node.operands)
    min = evaluate(node.operands[0])
    for op in node.operands[1:]:
        after = evaluate(op)
        if min >= after:
            return ATOMS[':false']
        min = after
    return ATOMS[':true']

def _gt_macro(node):
    all_numerics(node.operands)
    max = evaluate(node.operands[0])
    for op in node.operands[1:]:
        after = evaluate(op)
        if max <= after:
            return ATOMS[':false']
        max = after
    return ATOMS[':true']

def _le_macro(node):
    all_numerics(node.operands)
    min = evaluate(node.operands[0])
    for op in node.operands[1:]:
        after = evaluate(op)
        if min > after:
            return ATOMS[':false']
        min = after
    return ATOMS[':true']

def _ge_macro(node):
    all_numerics(node.operands)
    max = evaluate(node.operands[0])
    for op in node.operands[1:]:
        after = evaluate(op)
        if max < after:
            return ATOMS[':false']
        max = after
    return ATOMS[':true']

def _string_macro(node):
    compositon = lambda x: to_s(evaluate(x))
    return ' '.join(map(compositon, node.operands))

def _out_macro(node):
    compositon = lambda x: to_s(evaluate(x))
    result = ''.join(map(str, map(compositon, node.operands)))
    if conf.DEBUG:
        print('[out] --- <STDOUT>: `' + result + "'")
    else:
        sys.stdout.write(result)
    return result

def _puts_macro(node):
    compositon = lambda x: to_s(evaluate(x))
    result = '\n'.join(map(str, map(compositon, node.operands)))
    if conf.DEBUG:
        print('[puts] --- <STDOUT>: `' + result + "'")
    else:
        print(result)
    return result

def _let_macro(node):
    immediate_scope = CURRENT_SCOPES[-1]
    immediate_table = lookup_table(immediate_scope)
    for op in node.operands:
        if conf.DEBUG: print("let is defining: ", op.value.value)
        if conf.DEBUG: print("while alredy: ", lookup_table(CURRENT_SCOPES[-1]).local, "... exist\n\n")
        immediate_table.bind(op.value.value, evaluate(op.operands[0]))
    if conf.DEBUG: print('After let, defined variables in current scope, are: ', lookup_table(CURRENT_SCOPES[-1]).local)
    return

def _lambda_macro(node):
    table = SymbolTable(id(node), '_lambda', node)
    args = [node.operands[0].value] + node.operands[0].operands
    table.declare_args(list(map(lambda e: e.value, args)))
    TABLES.append(table)
    frozen = current_tables(CURRENT_SCOPES + [id(node)])
    frozen = [t.freeze() for t in frozen]
    return Definition(node.operands[1], table, args, frozen)

def _shorthand_macro(node):
    table = SymbolTable(id(node), '_short_lambda', node)
    table.declare_args('x')
    TABLES.append(table)
    frozen = current_tables(CURRENT_SCOPES + [id(node)])
    frozen = [t.freeze() for t in frozen]
    return Definition(node.operands[0], table, ['x'], frozen)

def _define_macro(node):
    name = node.operands[0].value.value  # Method name
    if conf.DEBUG: print("At time of definition of: '{}', scopes are: {}".format(name, list(map(str, current_tables(CURRENT_SCOPES)))))
    table = SymbolTable(id(node), name, node)
    TABLES.append(table)
    ops = list(map(lambda e: e.value, node.operands[0].operands))
    TABLES[-1].declare_args(ops)

    frozen = current_tables(CURRENT_SCOPES + [id(node)])
    frozen = [t.freeze() for t in frozen]
    definition = Definition(node.operands[1], table, ops, frozen)

    immediate_scope = CURRENT_SCOPES[-1]
    lookup_table(immediate_scope).bind(name, definition)

    return definition

MACROS = {
    'do': _do_macro,
    'prog': _do_macro,
    'yield': _yield_macro,
    'require': _require_macro,
    'eval': _eval_macro,
    'if': _if_macro,
    'unless': _unless_macro,
    'list': _list_macro,
    'size': _size_macro,
    'index': _index_macro,
    'push': _push_macro,
    'append': _push_macro,
    'unshift': _unshift_macro,
    'prepend': _unshift_macro,
    'concat': _concat_macro,
    'merge': _concat_macro,
    'concat!': _concat_des_macro,
    'merge!': _concat_des_macro,
    'pop': _pop_macro,
    'shift': _shift_macro,
    '<>': _composition_macro,
    '+': _add_macro,
    '-': _sub_macro,
    '*': _mul_macro,
    '/': _div_macro,
    '%': _mod_macro,
    '=': _eq_macro,
    '/=':_nq_macro,
    '!': _ne_macro,
    '&&': _and_macro,
    '||': _or_macro,
    '^^': _xor_macro,
    '<': _lt_macro,
    '>': _gt_macro,
    '<=':_le_macro,
    '>=':_ge_macro,
    'string': _string_macro,
    'out': _out_macro,
    'puts': _puts_macro,
    'let': _let_macro,
    'lambda': _lambda_macro,
    'λ': _lambda_macro,
    '->': _shorthand_macro,
    'define': _define_macro,
}

LAST_EVALUATED = tree.Nil(CURRENT_LOCATION)
LAST_RETURNED = LAST_EVALUATED

def evaluate(node):
    global TABLES, CURRENT_SCOPES, FROZEN_TABLES, CALL_STACK
    global EX, CURRENT_LOCATION, LAST_EVALUATED, LAST_RETURNED, ATOMS
    # All tables and scope/call stacks need to be
    # able to be modified by this method.

    if not is_node(node):
        LAST_EVALUATED = node
        return LAST_EVALUATED
                    # Anything that isn't an AST node will simply
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
        LAST_EVALUATED = node
        return LAST_EVALUATED  # Doesn't get evaluated per se.
    if node.type is tree.Nil:
        LAST_EVALUATED = node
        return LAST_EVALUATED  # Doesn't get evaluated per se.
    if node.type is tree.Atom:
        if node.value in ATOMS:
            LAST_EVALUATED = ATOMS[node.value]
            return LAST_EVALUATED
        ATOMS[node.value] = Atomise(node.value)
        LAST_EVALUATED = ATOMS[node.value]
        return LAST_EVALUATED
    if node.type is tree.Numeric:
        LAST_EVALUATED = node.value
        return LAST_EVALUATED
    if node.type is tree.Symbol:
        if node.value == '_':
            lookup_table(0x0).bind('_', LAST_RETURNED, mutable=True)
        if node.value in MACROS:
            LAST_EVALUATED = MACROS[node.value]
            return LAST_EVALUATED
        LAST_EVALUATED = search_tables(CURRENT_SCOPES, node.value)
        return LAST_EVALUATED
    if node.type is tree.Uneval:
        LAST_EVALUATED = node
        return LAST_EVALUATED  # Doesn't get evaluated per se.
    if node.type is tree.String:
        LAST_EVALUATED = node.value
        return LAST_EVALUATED
    if node.type is tree.Call:
        if node.value is None:
            EX.throw(node.location,
                'Cannot make empty call. Evaluating an\n'+
                'empty list does not make sense.')
        if node.value.type is tree.Symbol:
            method = node.value.value
            if conf.DEBUG: print("Calling symbolic method: ", repr(method))

            if method in MACROS:
                LAST_EVALUATED = MACROS[method](node)
                return LAST_EVALUATED

            LAST_EVALUATED = execute_method(node)
            return LAST_EVALUATED

        else:  # Not a symbol being called...
            LAST_EVALUATED = execute_method(node)
            return LAST_EVALUATED

    raise Exception("Don't know what to do with %s, this is a bug" % str(node))


def execute_method(node, args=None):
    global LAST_EVALUATED, LAST_RETURNED
    definition = node
    if not isinstance(node, (Definition, function)):
        definition = evaluate(node.value)

    if args is None:
        args = list(map(lambda e: evaluate(e), node.operands))

    if type(definition) is function:
        return definition(node)

    if type(definition) is not Definition:
        EX.throw(node.value.location,
            'Cannot make call to to type of `{}\''.format(
                to_type(definition)))

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

    LAST_EVALUATED = result
    LAST_RETURNED = LAST_EVALUATED
    return LAST_RETURNED


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
