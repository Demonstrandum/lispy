# LISPY
A LISP interpreter written in Python --- LIS(PY).


## About

### File Structure
```
├── common-lisp-merge-sort.lisp
├── debug-stages.py
├── docs
│   ├── ast_Tree.png
│   ├── carbon.png
│   ├── cons-cells.png
│   ├── debug-stages.png
│   ├── eof-string.png
│   ├── err-warn.png
│   ├── example_interp.png
│   ├── exec-args.png
│   ├── execute_file.png
│   ├── files.png
│   ├── hello-world-flowchart.png
│   ├── ilispy_file.png
│   ├── index-err.png
│   ├── interp-Atom.png
│   ├── interp-Def.png
│   ├── interp-eval.png
│   ├── interp-exec.png
│   ├── interp-load_file.png
│   ├── interp-req.png
│   ├── interp-SymTab.png
│   ├── interp-visit.png
│   ├── interp-walk.png
│   ├── lexer-flow.png
│   ├── lexer_regex.png
│   ├── lex_numeric.png
│   ├── main_lex.png
│   ├── mismatched-parens.png
│   ├── nea.pdf
│   ├── nea.tex
│   ├── num-call.png
│   ├── paren_bal.png
│   ├── parse-error.png
│   ├── parser_atom.png
│   ├── parser-flow.png
│   ├── parser_header.png
│   ├── parser_macroexpand.png
│   ├── parser_macro-obj.png
│   ├── parser_parse.png
│   ├── parser_pre.png
│   ├── prelude.png
│   ├── references.bib
│   ├── repl_lispy.png
│   ├── token_obj.png
│   ├── token_stream.png
│   ├── too-few-parens.png
│   ├── too-many-parens.png
│   ├── tree_Data.png
│   ├── tree_Hier.png
│   ├── tree_Nil.png
│   ├── tree_Node.png
│   ├── tree_Nodes.png
│   ├── tree_Operator.png
│   ├── type-check.png
│   └── unbound-sym.png
├── execute
├── hello_world.lispy
├── ilispy
├── LICENSE
├── lispy
│   ├── config.py
│   ├── err.py
│   ├── __init__.py
│   ├── lexing.py
│   ├── parsing.py
│   ├── tree.py
│   └── visitor.py
├── _making_log.log
├── prelude
│   ├── destructive.lispy
│   ├── dt.lispy
│   ├── functional.lispy
│   ├── IO.lispy
│   ├── lists.lispy
│   ├── loop.lispy
│   ├── numerics.lispy
│   └── prelude.lispy
├── README.md
├── repl.lispy
├── run-samples.sh
├── samples
│   ├── atoms.lispy
│   ├── blocks.lispy
│   ├── compose.lispy
│   ├── declarative.lispy
│   ├── deep.lispy
│   ├── eval.lispy
│   ├── factorial.lispy
│   ├── fizzbuzz.lispy
│   ├── functions.lispy
│   ├── ifact.lispy
│   ├── integral.lispy
│   ├── internal.lispy
│   ├── lists.lispy
│   ├── merge_sort.lispy
│   └── strings.lispy
├── testing.lispy
└── windows_execute.py

4 directories, 96 files
```

- The folder `lispy/` contains the implementation for the langauge.
- The folder `samples/` contains examples of LISPY programs.
- The folder `prelude/` contains the standard library for LISPY.
- The folder `/docs` contains the source for the documentation.
- The file `/docs/nea.pdf` is the compiled documentation document.


### How to execute a file
On GNU/Linux, in the root of this repository, type:
```shell
./execute <filename>
```
where `<filename>` is some file ending with `.lispy`.

### Running the REPL
On GNU/Linux, in the root of the repository again, type:
```shell
./ilispy
```
and the REPL should start.

### Weird file names:
`ast`, `parser` and `lexer` are reserved file names/modules in Python, so I
couldn't use those names.
