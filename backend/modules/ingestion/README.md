# Ingestion

Fetches and parses real source documents (government/NGO publications, WHO/UNICEF
guidance, health-ministry pages, vetted articles) about Swahili maternal and
newborn health, and lands them in `data/02_raw` and `data/03_extracted`.

Includes scraping utilities (web pages, PDFs) — kept in this module rather than
a separate `scraping/` folder, since scraping is just one technique ingestion uses,
not a separate pipeline stage.

**Input:** an approved entry in `data/01_source_register`
**Output:** raw file in `data/02_raw`, extracted text in `data/03_extracted`
**Owner track:** Data & Knowledge
**Sprint:** 1–2 (build), ongoing (add new sources)

Every source ingested here must already have a row in the source register —
ingestion never starts from a URL that hasn't been vetted first.
