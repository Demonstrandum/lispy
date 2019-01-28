import lexing
import tree
import err

DEBUG = True
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
    if DEBUG: print("TOP LEVEL PARSE: ", stream.current())
    branch = atom(stream.current(), stream)
    if branch is not None:
        AST.push(branch)
    if stream.ahead().type == 'EOF':
        return AST

    stream.next()
    return parse(stream, AST)

def atom(token, stream):
    if token.type == 'L_PAREN':
        caller = atom(stream.next(), stream)
        operands = []
        while stream.ahead().type != 'R_PAREN':
            if stream.current().type == 'EOF':
                EX.throw(
                    stream.current().location,
                    'Unexcpected EOF, missing closing parenthese'
                )
            operands.append(atom(stream.next(), stream))
        stream.next()  # Skip the R_PAREN we just spotted ahead.
        return tree.Call(caller, *operands)
    if token.type == 'NUMERIC':
        return tree.Numeric(numeric(token.string))
    if token.type == 'SYMBOL':
        return tree.Symbol(token.string)

    return None
    
        
