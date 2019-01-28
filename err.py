import sys

LEX   = 'Syntax Error'
PARSE = 'Parse Error'
EXEC  = 'Execution Error'

def Error(err_type, loc, string, file):
    lines = []
    with open(file, 'r') as f:
        lines = f.readlines()
    lines[-1] += '\0'
    
    snip = lines[loc['line'] - 1]
    snippet = '\n\nFile contents:      {line}| {snip}\n'.format(
        line = loc['line'],
        snip = snip
    )
    snippet += (' ' * (len(snippet) - len(snip) + loc['column'] - 4)) + '^\n'
    message = '[!!] - {kind} at ({line}:{col}) in file `{file}\':\n\t>>> {msg}'.format(
        kind = err_type,
        file = file,
        line = loc['line'], col = loc['column'],
        msg = string + ['.', ''][string[-1] in ['.', '!', '?']]
    )
    print(snippet + message)
    sys.exit(1)


class Thrower:
    def __init__(self, err_type, file):
        self.type = err_type
        self.file = file

    def throw(self, loc, string):
        return Error(self.type, loc, string, self.file)
