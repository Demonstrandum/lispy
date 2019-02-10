from . import err
import re, ast


EOF = '\0'

def exp(raw):
    return re.compile(raw)

# Identifiers are matched as such:
#   (Atoms and Symbols are the only identifiers)
SYMS = r"_A-Za-z\+\-\=\<\>\*\/\%\^\&\$\£\#\~\\\¬\,\.\?\!\@"
IDENT_STR = r"[{syms}][0-9\'{syms}]*".format(syms=SYMS)
                                         # e.g.
L_PAREN    = exp(r"\A\(")                # '('
R_PAREN    = exp(r"\A\)")                # ')'
NIL        = exp(r"\Anil")               # 'nil'
SYMBOL     = exp(r"\A" + IDENT_STR)      # 'hello-world'
UNEVAL     = exp(r"\A\'")                # '
ATOM       = exp(r"\A\:[0-9" + IDENT_STR[1:])  # ':good-bye'
NUMERIC    = exp(r"\A[0-9]+(\.[0-9]+)?([xob][0-9]+)?(e[\+\-]?)?[0-9a-fA-f]*")
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
impl_loc = {'line':'IMPLICIT','column':'IMPLICIT', 'filename':'IMPLICIT'}
class Token(object):
    def __init__(self, token_type, string, loc=impl_loc):
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
        def form(s):
            loc = [s.location['line'], s.location['column']]
            return '<Token({}) {} {} ... {}>'.format(
                s.type,
                '.' * (24 - (len(s.type) + len(str(loc)))),
                loc,
                repr(s.string)
            )
        return '\n'.join(map(form, self.tokens))

def lex(string, file):
    EX = err.Thrower(err.LEX, file)
    filename = str(file)

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
        if partial[:3] == 'nil':
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
                    EX.throw({'line': line, 'column': column},
                        'Unexpected EOF while reading string,\n'
                        + 'please check that you closed your quote...')
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

        column += 1
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

    return stream
