import sys

LEX   = 'Syntax'
PARSE = 'Parse'
EXEC  = 'Execution'

class c:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def Error(err_type, loc, string, file):
    lines = []
    with open(loc['filename'], 'r', newline=None) as f:
        lines = f.read()
    lines += '\0'
    lines = lines.split('\n')

    snip = lines[loc['line'] - 1]
    snippet = '\n    {b}{line}|{e} {w}{snip}{e}\n'.format(
        b = c.BOLD,
        w = c.WARNING,
        e = c.ENDC,
        file = loc['filename'],
        line = loc['line'],
        snip = snip
    )

    span = 1
    if 'span' in loc.keys():
        span = loc['span']
    snippet += (' ' * (len(snippet) - len(snip) + loc['column'] - 20)) + (c.BOLD + c.FAIL + '^' * span + c.ENDC)
    message = '{b}{f}[!!] - {kind} Error{e} at {b}({line}:{col}){e} in file `{u}{file}{e}\':\n\t{b}{w}>>>{e} {w}{msg}{e}'.format(
        b = c.BOLD,
        u = c.UNDERLINE,
        f = c.FAIL,
        w = c.WARNING,
        e = c.ENDC,
        kind = err_type,
        file = loc['filename'],
        line = loc['line'], col = loc['column'],
        msg  = '\n\t  '.join((string + ['.', ''][string[-1] in ['.', '!', '?']]).split('\n'))
    )
    where = '\n`{u}{file}{e}\' at:'.format(
        u = c.UNDERLINE,
        e = c.ENDC,
        file = loc['filename'])
    print(where + snippet + '\n' + message + '\n')
    sys.exit(1)


class Thrower:
    def __init__(self, err_type, file):
        self.type = err_type
        self.file = file

    def throw(self, loc, string):
        return Error(self.type, loc, string, self.file)
