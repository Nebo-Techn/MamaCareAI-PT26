# Raw

Untouched originals exactly as collected (saved PDFs, HTML dumps, saved
pages) — never hand-edited. Written by `backend/modules/ingestion`.

Why this stage exists even though it looks redundant with `03_extracted`: if
cleaned text downstream ever looks wrong, you need to be able to come back to
the actual original and check whether ingestion introduced the error or the
source itself was wrong. Deleting this "to save space" removes your ability
to audit the knowledge base later — don't.

**Owner track:** Data & Knowledge
