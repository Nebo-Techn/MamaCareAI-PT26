"""
Ports — the abstract interfaces the pipeline depends on.

DEPENDENCY INVERSION, CONCRETELY
`stages/translate.py` does not import `NLLBTranslator`. It imports
`ports.translator.Translator` — an abstract class. At runtime `container.py`
hands it whichever implementation the config asks for.

What this buys us, in order of importance to this project:
  1. Tests run with fakes. No API keys, no network, no GPU, no S3 in CI.
  2. The MVP runs free (SQLite, local disk, in-memory queue) and production
     runs at scale (Postgres, S3, SQS) with the same stage code.
  3. Swapping cloud MT for self-hosted NLLB — the open question in PDF
     section 6 — is a config change, not a rewrite. We do not have to answer
     that question before we start building.

INTERFACE SEGREGATION
Keep these interfaces small and single-purpose. One fat `Storage` port with
fifteen methods would force every fake in every test to implement all fifteen.
Instead we have `ObjectStore`, `SearchIndex`, and separate repositories —
each implementer only implements what it genuinely does.

RULE: no `import boto3` / `import httpx` / `import sqlalchemy` in this package.
Ports describe *what*, adapters decide *how*.
"""
