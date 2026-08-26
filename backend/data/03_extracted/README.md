# Extracted

Raw text pulled out of PDFs/HTML by the extract stage of
`backend/modules/pipeline`, before any cleaning and **before translation**.
Still messy on purpose — page headers, footnotes, broken line breaks are
expected here. Cleaning happens in the next stage, not this one.

Text here is still in its **source language** (English, French, whatever the
document was). Language detection, translation to Swahili, and human review
all happen after this point, inside the pipeline, before anything reaches
`04_cleaned`.

**Owner track:** Data & Knowledge
