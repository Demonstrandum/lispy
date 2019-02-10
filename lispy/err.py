import sys

LEX   = 'Syntax'
PARSE = 'Parse'
EXEC  = 'Execution'

def Error(err_type, loc, string, file):
    lines = []
    with open(loc['filename'], 'r', newline=None) as f:
        lines = f.read()
    lines += '\0'
    lines = lines.split('\n')

    snip = lines[loc['line'] - 1]
    snippet = '\n`{file}\' at:      {line}| {snip}\n'.format(
        file = loc['filename'],
        line = loc['line'],
        snip = snip
    )

    span = 1
    if 'span' in loc.keys():
        span = loc['span']
    snippet += (' ' * (len(snippet) - len(snip) + loc['column'] - 3)) + ('^' * span)
    message = '[!!] - {kind} Error at ({line}:{col}) in file `{file}\':\n\t>>> {msg}'.format(
        kind = err_type,
        file = loc['filename'],
        line = loc['line'], col = loc['column'],
        msg  = '\n\t  '.join((string + ['.', ''][string[-1] in ['.', '!', '?']]).split('\n'))
    )
    print(snippet + '\n' + message + '\n')
    sys.exit(1)


class Thrower:
    def __init__(self, err_type, file):
        self.type = err_type
        self.file = file

    def throw(self, loc, string):
        return Error(self.type, loc, string, self.file)
