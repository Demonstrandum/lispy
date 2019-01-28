Files, in order of usage:

	- `lexing.py`:  Contains code for token stream and converts the
		written program into a stream of tokens.

	- `tree.py`:    Outlines classes for AST and its nodes, as well
		as confusing code for visualising the tree.

	- `parsing.py`:  The parser goes through the token stream provided
		by lexing.py, then assembles a tree based on the components
		provided by tree.py

	- `visitor.py`:  The visitor visits the tree, evaluating every
		node of the tree, thus executing the code, by evaluating
		bottom-up.
	
	- `sample.txt`:  The sample file, contains example code for the
		interpreter to interpret.  To run the file, simply run the
		visitor.py file

# How it works:
This interpreter works quite differently from most LISP interpreters,
as it does not work by using a REPL (Read-Eval-Print-Loop `(loop (print (eval (read))))` ).
Instead it will read the whole file and then step through the AST.

# Weird file names:
`ast`, `parser` and `lexer` are reserved file names/modules in python, so I
couldn't use those names.


