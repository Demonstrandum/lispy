from . import lexing
from . import tree

from . import err
from . import config as conf

EOF = '\0'

EX = None

def numeric(string):
    if '.' in string:
        return float(string)
    return int(string)

def parse(stream, AST=None):
    global EX
    if EX is None :
        EX = err.Thrower(err.PARSE, stream.file)
    if AST is None:
        AST = tree.Tree(stream.file)
        stream.purge('TERMINATOR')
    if conf.DEBUG: print("TOP LEVEL PARSE: ", stream.current())
    branch = atom(stream.current(), stream)
    if branch is not -1:
        if conf.DEBUG: print('Adding branch: ', branch.type)
        AST.push(branch)
    if stream.ahead().type == 'EOF':
        return AST

    stream.next()
    return parse(stream, AST)

def atom(token, stream):
    if conf.DEBUG: print('Atomic token type: ', token.type)
    loc = token.location

    if token.type == 'L_PAREN':
        caller = None
        if stream.ahead().type != 'R_PAREN':
            caller = atom(stream.next(), stream)
        else:
            stream.next() # Go past the R_PAREN, so outer calls don't get closed
            return tree.Call(caller, loc)
        operands = []
        while stream.ahead().type != 'R_PAREN':
            if stream.current().type == 'EOF':
                EX.throw(
                    stream.current().location,
                    'Unexcpected EOF, missing closing parenthesis')
            operands.append(atom(stream.next(), stream))
        stream.next()  # Skip the R_PAREN we just spotted ahead.
        if caller.value == 'yield':
            return tree.Yield(operands[0], loc)
        return tree.Call(caller, loc, *operands)
    if token.type == 'NUMERIC':
        return tree.Numeric(numeric(token.string), loc)
    if token.type == 'SYMBOL':
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
