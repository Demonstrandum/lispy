import copy

class Tree(list):
    def __init__(self, file):
        self.file = file
        list.__init__(self)
    def push(self, *arg):
        return self.append(*arg)
    def __str__(self):
        rep = ''
        for e in self:
            rep += u'\u2503\n\u2523\u2501' + str(e) +'\n'
        return rep


TAB = ' ' * 3
class Node(object):
    scope = None
    def __init__(self, value, loc):
        self.value = value
        self.type = self.__class__
        self.name = str(self.type).split('.')[-1][:-2]
    def __str__(self, depth=0):
        return "{}<AST::Node[{}] ({})>".format(
            '' if depth == 0 else TAB * 2,
            self.name,
            [str, repr][type(self.value) is str](self.value)
        )


class Operator(Node):
    def __init__(self, value, loc, *operands):
        self.location = loc
        self.operands = list(operands)
        self.value = value
        self.type = self.__class__
        self.name = str(self.type).split('.')[-1][:-2]
        self.shorthand = None
    def __deepcopy__(self, memodict={}):
        return self.__class__(copy.deepcopy(self.value), self.location, *(copy.deepcopy(self.operands)))
    def __str__(self, depth=0):  # Don't even try to understand this.
        operands = '\n'.join(
            map(lambda e: (u'\u2503{}'.format(TAB * ([1, 2][depth>0] + depth) + (e.__str__(depth + 1) if issubclass(type(e), Node) else str(e)))), self.operands)
        )
        caller_lines = self.value.__str__().split('\n')
        caller = '\n{}'.format(TAB*(depth+2) + ' ').join(caller_lines)
        return u"{ind}<AST::Node[{}]\n\u2503{ind1}\u2523\u2501caller\n\u2503{ind1}\u2503  \u2517\u2501{}\n\u2503{ind1}\u2517\u2501operands=[".format(
            self.name,
            caller,
            ind = '' if depth == 0 else TAB * 2,
            ind1 = TAB * (depth+2) if depth == 0 else TAB * (depth + 3)
        ) + (']>' if len(self.operands) == 0 else ('\n' + operands + u'\n\u2503  {}]>'.format(TAB * (depth + [2,3][depth>0]))))

class Data(Node):
    def __init__(self, value, loc):
        self.location = loc
        self.value = value
        self.type = self.__class__
        self.name = str(self.type).split('.')[-1][:-2]
    def __deepcopy__(self, memodict={}):
        return  self.__class__(copy.deepcopy(self.value), self.location)

class Nil(Node):
    def __init__(self, loc):
        self.location = loc
        self.value = 'nil'
        self.type = self.__class__
        self.name = str(self.type).split('.')[-1][:-2]
    def __deepcopy__(self, memodict={}):
        return self
    def __hash__(self):
        return hash(self.value)

# Declare children classes

class Yield(Data):
    pass

class Call(Operator):
    pass

class Symbol(Data):
    pass

class Atom(Data):
    pass

class Numeric(Data):
    pass

class Uneval(Data):
    def __hash__(self):
        return hash(self.value)

class String(Data):
    def __hash__(self):
        return hash(self.value)
