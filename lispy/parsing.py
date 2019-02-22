from . import lexing
from . import tree

from . import err
from . import config as conf

import sys, copy, ast, re

EOF = '\0'

EX = None

def numeric(string, location):
    try:
        return ast.literal_eval(string)
    except:
        return EX.throw(location,
            'Could not parse `{}\' as a numeric, malformed literal.'.format(string))

class Macro(object):
    def __init__(self, subtree):
        self.tree = copy.deepcopy(subtree)
        self.name = self.tree.operands[1].value.value
        self.args = list(map(lambda e: e.value, self.tree.operands[1].operands))
        self.body = self.tree.operands[2]
        self.quoted = tree.Uneval(self.body, self.body.location)

    def invoke(self, caller):
        if len(caller.operands) != len(self.args):
            return EX.throw(caller.location,
                'Incorrect number of arguments to macro!\n'
                + 'Expected {} arguments, got {}'.format(
                    len(self.args), len(caller.operands)))

        name_map = {}
        for i in range(len(self.args)):
            name_map[self.args[i]] = tree.Uneval(caller.operands[i], caller.location)

        if issubclass(type(self.body), tree.Data) and type(self.body) is not tree.Uneval:
            if type(self.body) is tree.Symbol and self.body.value in self.args:
                return name_map[self.body.value]
            return self.body

        body = copy.deepcopy(self.body)
        def replace_args(subtree, parent):
            if not issubclass(type(subtree), tree.Node):
                return None
            if (type(subtree) is tree.Symbol
            and subtree.value in self.args):
                if parent is None:
                    body = name_map[parent.value]
                if issubclass(type(parent), tree.Operator):
                    if parent.value.value in self.args:
                        parent.value = name_map[parent.value.value]
                    for i in range(len(parent.operands)):
                        name = parent.operands[i].value
                        if name in self.args:
                            parent.operands[i] = name_map[name]
                else:
                    if type(parent) is tree.Uneval:
                        parent.value = name_map[parent.value.value]

            replace_args(subtree.value, subtree)
            if issubclass(type(subtree), tree.Operator):
                for i in range(len(subtree.operands)):
                    replace_args(subtree.operands[i], subtree)
            return None


        replace_args(body, None)
        return body


MACROS = {}

def macro_expansion(ast, i):
    def search_brach(subtree, parent=None):
        t = type(subtree)

        if issubclass(t, tree.Operator):
            found = False
            operands = subtree.operands
            if (issubclass(type(subtree.value), tree.Node)
            and subtree.value.value == 'define'
            and len(subtree.operands) > 0
            and type(subtree.operands[0]) is tree.Symbol
            and subtree.operands[0].value == 'macro'):
                caller = subtree.operands[1]
                found = type(caller.value.value) is str
                operands = subtree.operands[2:]
            else:
                if type(subtree.value) is tree.Symbol:
                    if subtree.value.value in MACROS:
                        replacement = MACROS[subtree.value.value].invoke(subtree)
                        if parent is None:
                            ast[i] = replacement
                        else:
                            if parent.value == subtree:
                                parent.value = replacement
                            else:
                                for j in range(len(parent.operands)):
                                    if parent.operands[j] == subtree:
                                        parent.operands[j] = replacement
                                        break

            search_brach(subtree.value, parent=subtree)
            for operand in operands:
                search_brach(operand, parent=subtree)

            if found:
                MACROS[caller.value.value] = Macro(subtree)
                empty_branch = tree.Nil(subtree.location)
                if parent is None:
                    ast[i] = empty_branch
                else:
                    if parent.value == subtree:
                        parent.value = empty_branch
                    else:
                        for j in range(len(parent.operands)):
                            if parent.operands[j] == subtree:
                                parent.operands[j] = empty_branch
                                break
            return None

        if issubclass(t, tree.Data):
            if subtree.value in MACROS:
                if parent is None:
                    ast[i] = MACROS[subtree.value].quoted
                else:
                    if issubclass(type(parent), tree.Operator):
                        if parent.value.value == subtree.value:
                            replacement = MACROS[subtree.value].invoke(parent)
                            if issubclass(type(replacement), tree.Operator):
                                parent.value = replacement.value
                                parent.operands = replacement.operands
                            else:
                                parent = replacement
                        else:
                            for j in range(len(parent.operands)):
                                if parent.operands[j].value == subtree.value:
                                    parent.operands[j] = MACROS[subtree.value].quoted
            else:
                search_brach(subtree.value, parent=subtree)
        return None

    search_brach(ast[i])
    return ast[i]

def preprocess(AST, macros={}):
    global MACROS
    MACROS = macros  # Clear the known macros, such that
                     #   any subsequent instances of the parser
                     #   don't use old macros, irrelevent to them
                     #   (and to avoid name clashes...)

    for i in range(len(AST)):
        AST[i] = macro_expansion(AST, i)
    return AST

def parse(stream, string=None):
    global EX
    AST = None
    if EX is None :
        EX = err.Thrower(err.PARSE, stream.file)
        if string is not None:
            EX.nofile(string)
    if AST is None:
        AST = tree.Tree(stream.file)
        stream.purge('TERMINATOR')

    def parse_loop(AST):
        if conf.DEBUG: print("TOP LEVEL PARSE: ", stream.current())
        branch = atom(stream.current(), stream)
        if branch is not -1:
            if conf.DEBUG: print('Adding branch: ', branch.type)
            AST.push(branch)
        if stream.ahead().type == 'EOF':
            return AST

        stream.next()
        return parse_loop(AST)

    AST = parse_loop(AST)
    if conf.DEBUG: print("Size of AST:", sys.getsizeof(AST))
    return AST

SHORTHAND = None

def atom(token, stream):
    global SHORTHAND
    if conf.DEBUG: print('Atomic token type: ', token.type)
    loc = token.location

    if token.type == 'L_PAREN':
        SHORTHAND = 0
        caller = None
        if stream.ahead().type != 'R_PAREN':
            caller = atom(stream.next(), stream)
        else:
            stream.next() # Go past the R_PAREN, so outer calls don't get closed
            return tree.Call(caller, loc)
        operands = []
        while stream.ahead().type != 'R_PAREN':
            if stream.current().type == 'EOF':
                return EX.throw(
                    stream.current().location,
                    'Unexcpected EOF, missing closing parenthesis')
            operands.append(atom(stream.next(), stream))
        stream.next()  # Skip the R_PAREN we just spotted ahead.
        if caller.value == 'yield':
            if len(operands) == 0:
                operands.append(tree.Nil(loc))
            return tree.Yield(operands[0], loc)
        call = tree.Call(caller, loc, *operands)
        if (caller.type is tree.Symbol
        and caller.value == '->'):
            call.shorthand = SHORTHAND
            SHORTHAND = None
        return call
    if token.type == 'NUMERIC':
        return tree.Numeric(numeric(token.string, loc), loc)
    if token.type == 'SYMBOL':
        if SHORTHAND is not None and re.match(r"\%[1-9]+", token.string):
            SHORTHAND += 1
        return tree.Symbol(token.string, loc)
    if token.type == 'ATOM':
        return tree.Atom(token.string, loc)
    if token.type == 'UNEVAL':
        return tree.Uneval(atom(stream.next(), stream), loc)
    if token.type == 'STRING':
        return tree.String(token.string, loc)
    if token.type == 'NIL':
        return tree.Nil(loc)

    return -1
