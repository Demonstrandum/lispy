import lexing
import tree

DEBUG = False

EOF = '\0'

def numeric(string):
    if '.' in string:
        return float(string)
    return int(string)

def parse(stream, AST=None):
    if AST is None:
        AST = tree.Tree()
    if DEBUG: print("TOP LEVEL PARSE: ", stream.current())
    branch = atom(stream.current(), stream)
    if branch is not None:
        AST.push(branch)
    if stream.ahead() == EOF:
        return AST

    stream.next()
    return parse(stream, AST)

def atom(token, stream):
    if token.type == 'L_PAREN':
        caller = atom(stream.next(), stream)
        operands = []
        while stream.ahead().type != 'R_PAREN':
            operands.append(atom(stream.next(), stream))
        stream.next()  # Skip the R_PAREN we just spotted ahead.
        return tree.Call(caller, *operands)
    if token.type == 'NUMERIC':
        return tree.Numeric(numeric(token.string))
    if token.type == 'SYMBOL':
        return tree.Symbol(token.string)

    return None
    
        
