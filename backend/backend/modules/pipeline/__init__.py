"""
Multilingual data collection pipeline.

Collects resources from heterogeneous sources (web links, video links, PDFs),
detects their source language, translates them into Swahili, stores every
artifact, and routes the translated output through human review before it is
published as vetted MamaCare AI knowledge.

Read `README.md` in this folder before writing any code here. It explains the
layering rule that the whole module depends on:

    domain/   <- pure Python. Knows nothing about HTTP, S3, Postgres, or MT APIs.
    ports/    <- abstract interfaces. What the pipeline NEEDS.
    stages/   <- use cases. Orchestrates ports. Never imports adapters/.
    adapters/ <- concrete implementations. What actually DOES the work.
    container.py <- the ONLY place that knows which adapter fills which port.

Imports point inward only: adapters -> ports -> domain. If you ever find
yourself writing `from ..adapters...` inside `stages/`, stop — that is the
bug this layout exists to prevent.
"""
