import lispy
import codecs

# Let's first read the contents of the file
#   as a string into a variable.
TESTING_FILE = './testing.lispy'

PROGRAM_STRING = None
with codecs.open(TESTING_FILE, 'r', 'utf-8') as file:
    PROGRAM_STRING = file.read()  # Read from the file.


# === Lexing === #
#   The lex method will reduce the program string
#   into a TokenStream.
stream = lispy.lexing.lex(PROGRAM_STRING, TESTING_FILE)

print("\n\n=== Token Stream ===\n")
print(stream)  # Here we print the stream out.


# === Parsing === #
#   We call the parse method on the stream
#   and it will return an AST (parse tree).
ast = lispy.parsing.parse(stream)

print("\n\n=== Abstract Syntax Tree ===\n")
print(ast)  # Print a visualisation of the tree.

# === Macro Expansion === #
#   Here we search and invoke and replace macros
#   in the parse tree.
expanded = lispy.parsing.preprocess(ast)

print("\n\n=== Macro Expanded ===\n")
print(expanded)
