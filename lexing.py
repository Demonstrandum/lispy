import re


EOF = '\0'

def exp(raw):
    return re.compile(raw)

IDENT_STR = r"[_A-Za-z\+\-\*\/\?\!][0-9\'a-zA-Z_\-\*\+\/\?\!]*"

L_PAREN    = exp(r"\A\(")
R_PAREN    = exp(r"\A\)")
SYMBOL     = exp(r"\A" + IDENT_STR)
UNEVAL     = exp(r"\A\'")
ATOM       = exp(r"\A(\:)" + IDENT_STR)
NUMERIC    = exp(r"[0-9]+(\.[0-9]+)?([xob][0-9]+)?(e[\+\-]?)?[0-9a-fA-f]*")
TERMINATOR = exp(r"\n")

class Token(object):
    def __init__(self, token_type, string, loc={'line':'IMPLICIT','column':'IMPLICIT'}):
        self.type = token_type
        self.string = string
        self.location = loc
        self.location['span'] = len(string)
        
    def __str__(self):
        return "<Token({}) '{}'>".format(
            self.type,
            self.string
        )

EOF_TOKEN = Token('EOF', EOF)

class TokenStream(object):
    def __init__(self, file, tokens = None):
        self.file = file
        self.tokens = tokens or []
        self.i = 0

    def current(self):
        if self.i >= self.size():
            return EOF_TOKEN
        return self.tokens[self.i]

    def size(self):
        return len(self.tokens)

    def push(self, token):
        if type(token) is list:
            for elem in token:
                self.tokens.append(elem)
        else:
            self.tokens.append(token)
        return self.tokens
    add = push

    def pop(self, j = -1):
        return self.tokens.pop(j)
        
    def next(self, j = 1):
        self.i += j
        if self.i >= self.size():
            return EOF_TOKEN
        return self.tokens[self.i]

    def ahead(self, j = 1):
        if self.i + j >= self.size():
            return EOF_TOKEN
        return self.tokens[self.i + j]

    def back(self, j = 1):
        self.i -= j
        return self.tokens[self.i]

    def behind(self, j = 1):
        return self.tokens[self.i - j]

    def __str__(self):
        def form(s):
            loc = [s.location['line'], s.location['column']]
            return '<Token({}) {} {} ... "{}">'.format(
                s.type,
                '.' * (24 - (len(s.type) + len(str(loc)))),
                loc,
                s.string
            )
        return '\n'.join(map(form, self.tokens))

def lex(string, file):
    string += EOF
    stream = TokenStream(file)
    i = 0
    line = 1
    column = 1

    match = None
    while i < len(string):
        partial = string[i::]

        # Add EOF token at End Of File:
        if partial[0] == EOF:
            stream.add(Token('EOF', partial[0], {
                'line': line,
                'column': column
            }))
            break
        
        # Ignore comments, we dont need them in our token stream.
        if partial[0] == ';':
            j = 0
            while partial[j] != '\n' and partial[j] != EOF:
                j += 1
            i += j
            column += j
            continue

        # Match L_PAREN
        if partial[0] == '(':
            stream.add(Token('L_PAREN', partial[0], {
                'line': line,
                'column': column
            }))
            i += 1
            column += 1
            continue
        
        # Match R_PAREN
        if partial[0] == ')':
            stream.add(Token('R_PAREN', partial[0], {
                'line': line,
                'column': column
            }))
            i += 1
            column += 1
            continue

        # Match unevaluator
        if partial[0] == "'":
            stream.add(Token('UNEVAL', "'", {
                'line': line,
                'column': column
            }))
            i += 1
            column += 1
            continue

        # Match an atom
        match = ATOM.match(partial)
        if match:
            stream.add(Token('ATOM', match.group(), {
                'line': line,
                'column': column
            }))
            span = len(match.group())
            i += span
            column += span
            continue

        # Match a symbol
        match = SYMBOL.match(partial)
        if match:
            stream.add(Token('SYMBOL', match.group(), {
                'line': line,
                'column': column
            }))
            span = len(match.group())
            i += span
            column += span
            continue

        # Match a numeric
        match = NUMERIC.match(partial)
        if match:
            stream.add(Token('NUMERIC', match.group(), {
                'line': line,
                'column': column
            }))
            span = len(match.group())
            i += span
            column += span
            continue

        column += 1
        if partial[0] == "\n":
            stream.add(Token('TERMINATOR', r"\n", {
                'line': line,
                'column': column - 1
            }))
            i += 1
            line += 1
            column = 1
            continue
        i += 1
    return stream

    
