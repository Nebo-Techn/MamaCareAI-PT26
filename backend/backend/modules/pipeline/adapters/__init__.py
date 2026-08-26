"""
Adapters — the concrete implementations of the ports.

This is the only layer allowed to import third-party infrastructure libraries:
httpx, boto3, sqlalchemy, pymupdf, fasttext, transformers.

THE ONE RULE: nothing imports FROM here except `container.py`.
If `stages/translate.py` imports `NLLBTranslator`, the design is broken — the
stage is now untestable without a GPU and un-switchable without an edit.

Each adapter is small and does one thing. When an adapter starts making
decisions ("should we translate this?"), that logic belongs in a stage. When a
stage starts knowing about HTTP status codes, that belongs in an adapter.
"""
