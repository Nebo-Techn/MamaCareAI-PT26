# Shared

Cross-cutting utilities used by more than one module: Swahili text helpers,
logging setup, shared constants.

Rule: don't put something here until at least two modules actually need it.
A `shared/` folder that gets used as a dumping ground for one-off helpers is
how codebases rot — if only `modules/rag` needs it, it lives in
`modules/rag`.

**Owner track:** shared, whoever needs it first
