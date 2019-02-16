import sys

from . import tree
from . import config as conf

LEX   = 'Syntax'
PARSE = 'Parse'
EXEC  = 'Execution'

def err_print(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

class c:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def Message(message_type):
    def TypeOfMessage(err_type, loc, string, file, prog=None):
        lines = ""
        if prog is not None:
            lines = prog + '\0'
            lines = lines.split('\n')
        else:
            try:
                with open(loc['filename'], 'r', newline=None) as f:
                    lines = f.read()
                lines += '\0'
                lines = lines.split('\n')
            except:
                lines = "NO_FILE_AVAILABLE"

        snip = lines[-1]
        if loc['line'] <= len(lines):
            snip = lines[loc['line'] - 1]

        snippet = '\n    {b}{line}|{e} {w}{snip}{e}\n'.format(
            b = c.BOLD,
            w = c.WARNING,
            e = c.ENDC,
            line = loc['line'],
            snip = snip
        )

        span = 1
        if 'span' in loc.keys():
            span = loc['span']
        snippet += (' ' * (len(snippet) - len(snip) + loc['column'] - 20)) + (c.BOLD + c.FAIL + '^' * span + c.ENDC)
        message = '{b}{f}[{lev}] - {kind} {msg_type}{e} at {b}({line}:{col}){e} in {where} `{u}{file}{e}\':\n\t{b}{w}>>>{e} {w}{msg}{e}'.format(
            b = c.BOLD,
            u = c.UNDERLINE,
            f = [c.FAIL, c.HEADER][message_type == 'Warning'],
            w = [c.WARNING, c.OKBLUE][message_type == 'Warning'],
            e = c.ENDC,
            lev = ['**', '!!'][message_type == 'Error'],
            msg_type = message_type,
            kind = err_type,
            where = ['file', 'string'][prog is not None],
            file = [loc['filename'], 'in eval call'][prog is not None],
            line = loc['line'], col = loc['column'],
            msg  = '\n\t  '.join((string + ['.', ''][string[-1] in ['.', '!', '?']]).split('\n'))
        )
        where = '\n`{u}{file}{e}\' at:'.format(
            u = c.UNDERLINE,
            e = c.ENDC,
            file = loc['filename'])
        err_print(where + snippet + '\n' + message + '\n')

        if not conf.EXIT_ON_ERROR:
            return tree.Nil({'line': 'ERROR', 'column': 'ERROR', 'filename': 'ERROR'})
        if message_type == 'Error':
            sys.exit(1)
        return 1
    return TypeOfMessage

Error = Message('Error')
Warn  = Message('Warning')


class Thrower:
    def __init__(self, err_type, file):
        self.type = err_type
        self.file = file
        self.prog = None
    def nofile(self, prog):
        self.prog = prog

    def throw(self, loc, string):
        return Error(self.type, loc, string, self.file, self.prog)
    def warn(self, loc, string):
        return Warn(self.type, loc, string, self.file, self.prog)
