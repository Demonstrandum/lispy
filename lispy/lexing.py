from . import err
import re, ast

import copy

EOF = '\0'

# Alias the regex compiler
exp = re.compile

# Identifiers are matched as such:
#   (Atoms and Symbols are the only identifiers)
SYMS = r"_a-zA-Zα-ωΑ-Ω\+\-\=\<\>\*\/\%\^\&\:\$\£\#\~\`\|\\\¬\,\.\?\!\@"
IDENT_STR = r"[{syms}][0-9\'{syms}]*".format(syms=SYMS)
                                         # e.g.
L_PAREN    = exp(r"\A\(")                # '('
R_PAREN    = exp(r"\A\)")                # ')'
NIL        = exp(r"\Anil")               # 'nil'
SYMBOL     = exp(r"\A" + IDENT_STR)      # 'hello-world'
UNEVAL     = exp(r"\A\'")                # '
ATOM       = exp(r"\A\:+[0-9" + IDENT_STR[1:])  # ':good-bye'
NUMERIC    = exp(r"\A[0-9]+(\.[0-9]+)?([xob][0-9a-fA-F]+)?(e[\+\-]?)?[0-9a-fA-F]*")
TERMINATOR = exp(r"\A\n")
STRING     = exp(r"\A([\"'])((\\{2})*|(.*?[^\\](\\{2})*))\1")
# `Token` object is a chunk of the code we're interpreting;
#         it holds the type of thing it is as well as what
#         exactly the writer has written and at what line and
#         column it was written as
# i.e.  (a 3)    ==>    <Token[L_PAREN] '(' (1:1)>,
#                       <Token[SYMBOL]  'a' (1:2)>,
#                       <Token[NUMERIC] '3' (1:4)>,
#                       <Token[R_PAREN] ')' (1:5)>
impl_loc = {'line':-1,'column':-1, 'filename':'IMPLICIT'}
class Token(object):
    def __init__(self, token_type, string, loc=impl_loc):
        self.type = token_type
        self.string = string
        self.location = loc
        self.location['span'] = len(string) + [0, 2][self.type == 'STRING']

    def __str__(self):
        return "<Token({}) '{}' ({}:{}) [span: {}]>".format(
            self.type,
            self.string,
            self.location['line'],
            self.location['column'],
            self.location['span']
        )

EOF_TOKEN = Token('EOF', EOF)

# `TokenStream` is a wrapper for a list of tokens
#               to make it easier to manage what token we're
#               currently focused on.
class TokenStream(object):
    def __init__(self, file, tokens = None):
        self.file = file
        self.tokens = tokens or []
        self.i = 0

    # Simply returns the token that is at `self.i`,
    #   the streams current focused token.
    def current(self):
        if self.i >= self.size():
            return EOF_TOKEN
        return self.tokens[self.i]

    # Returns the amount of tokens in the stream.
    def size(self):
        return len(self.tokens)

    # Pushes on top of the token stream stack.
    def push(self, token):
        if type(token) is list:
            for elem in token:
                self.tokens.append(elem)
        else:
            self.tokens.append(token)
        return self.tokens
    add = push

    # Pops off the top of the token stream stack.
    def pop(self, j = -1):
        return self.tokens.pop(j)

    # `next` will step forward in the token stream, and set
    #        the current token to the one after the current one.
    def next(self, j = 1):
        self.i += j
        if self.i >= self.size():
            return EOF_TOKEN
        return self.tokens[self.i]

    # `ahead` will peak ahead in the token stream, and return the token
    #         right after the current token.
    def ahead(self, j = 1):
        if self.i + j >= self.size():
            return EOF_TOKEN
        return self.tokens[self.i + j]

    # `back` takes a step back and sets the current token to the one before now.
    def back(self, j = 1):
        self.i -= j
        return self.tokens[self.i]

    # `behind` simply returns the token before the current.
    def behind(self, j = 1):
        return self.tokens[self.i - j]

    # `purge` will remove all tokens of a certain kind.
    def purge(self, type):
        new = []
        for e in self.tokens:
            if e.type != type:
                new.append(e)
        self.tokens = new
        return new

    def __str__(self):
        def form(s): # A nice string repr. of the stream.
            loc = [s.location['line'], s.location['column']]
            return '<Token({}) {} {} ... {}>'.format(
                s.type,
                '.' * (24 - (len(s.type) + len(str(loc)))),
                loc,
                repr(s.string)
            )
        return '\n'.join(map(form, self.tokens))

# Simple stack-based algo for checking the amount of
#  opening parens to the amount of closing, and giving a
#  helpful error message
def paren_balancer(stream):
    stream = copy.copy(stream)  # Create a shallow copy of the stream
    stack = []                  # in order to derefrence the original stream.
    balanced = True
    location = None

    while stream.current() != EOF_TOKEN:
        location = stream.current().location
        if stream.current().type == 'L_PAREN':
            stack.append(0)
        elif stream.current().type == 'R_PAREN':
            if len(stack) == 0:
                balanced = False
                break
            else:
                stack.pop()

        stream.next()

    opens = 0
    close = 0
    for t in stream.tokens: # Keep track of opens vs. closes
        if t.type == 'L_PAREN': opens += 1
        if t.type == 'R_PAREN': close += 1

    # If the stack is empty, we've too many, otherwise to little closing parens.
    message = ('Unbalanced amount of parentheses,\n'
        + 'consider removing {} of them...'.format(close - opens))
    if len(stack) != 0:
        location = stream.tokens[-2].location
        message = 'Missing {} closing parentheses...'.format(len(stack))
    elif close - opens < 1:
        message = 'Invalid arrangement of parentheses, this means nothing.'
    return {
        'balanced': balanced and len(stack) == 0,
        'location': location,
        'message': message
    }

def lex(string, file, nofile=False):
    EX = err.Thrower(err.LEX, file)
    filename = file
    if nofile:
        EX.nofile(string)

    string += EOF
    stream = TokenStream(file)
    i = 0
    line = 1  # Initialise location variables
    column = 1

    match = None # Loop though the string, shifting off the string list.
    while i < len(string):
        partial = string[i::] # Match against the program, cut off slightly
                              # more every time.

        # Add EOF token at End Of File:
        if partial[0] == EOF:
            stream.add(Token('EOF', partial[0], {
                'line': line,
                'column': column,
                'filename': filename
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
                'column': column,
                'filename': filename
            }))
            i += 1
            column += 1
            continue

        # Match R_PAREN
        if partial[0] == ')':
            stream.add(Token('R_PAREN', partial[0], {
                'line': line,
                'column': column,
                'filename': filename
            }))
            i += 1
            column += 1
            continue

        # Match Nil token
        if partial[:3] == 'nil' and not SYMBOL.match(partial[3]):
            stream.add(Token('NIL', partial[:3], {
                'line': line,
                'column': column,
                'filename': filename
            }))
            i += 3
            column += 3
            continue

        # Match unevaluator
        if partial[0] == "'":
            stream.add(Token('UNEVAL', "'", {
                'line': line,
                'column': column,
                'filename': filename
            }))
            i += 1
            column += 1
            continue

        # Match string
        if partial[0] == '"':
            contents = ""
            j = 1
            loc = {'line': line, 'column': column, 'filename': filename}
            while partial[j] != '"':
                if partial[j+1] == EOF:
                    l = {'line': line, 'column': column+1, 'filename': filename}
                    EX.throw(l,
                        'Unexpected EOF while reading string,\n'
                        + 'please check that you closed your quote...')
                    stream = TokenStream(stream.file)
                    stream.add(Token('NIL', 'nil', l))
                    return stream
                if partial[j] == '\n':
                    contents += '\\n'
                    line += 1
                    column = 1
                    j += 1
                    continue
                if partial[j] == '\\':
                    contents += '\\' + partial[j+1]
                    j += 2
                    column += 1
                    continue
                contents += partial[j]
                column += 1
                j += 1

            contents = '"' + contents + '"'
            stream.add(Token('STRING', ast.literal_eval(contents), loc))
            i += j + 1
            column += 2
            continue

        # Match an atom
        match = ATOM.match(partial)
        if match:
            stream.add(Token('ATOM', match.group(), {
                'line': line,
                'column': column,
                'filename': filename
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
                'column': column,
                'filename': filename
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
                'column': column,
                'filename': filename
            }))
            span = len(match.group())
            i += span
            column += span
            continue

        column += 1 # Terminators are useless, but I might use them.
        if partial[0] == "\n":
            stream.add(Token('TERMINATOR', "\n", {
                'line': line,
                'column': column - 1,
                'filename': filename
            }))
            i += 1
            line += 1
            column = 1
            continue
        i += 1

    # Check we have a balanced amount of L_PARENS to R_PARENS
    balancer = paren_balancer(stream)
    if not balancer['balanced']:
        EX.throw(balancer['location'], balancer['message'])
        stream = TokenStream(stream.file)
        stream.add(Token('NIL', 'nil', balancer['location']))

    return stream
