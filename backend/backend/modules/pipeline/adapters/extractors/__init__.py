"""
Extractors — bytes in, NormalizedDocument out (PDF 3.2).

THE FALLBACK CHAIN, EXPRESSED AS PRIORITIES (registered in container.py):

    html_extractor        100    text/html
    pdf_text_extractor    100    PDFs that have a real text layer
    pdf_ocr_extractor      50    scanned PDFs  <- expensive, only on fallthrough
    caption_extractor     100    videos with captions
    asr_extractor          50    videos without  <- most expensive step, last resort

The registry tries high priority first and takes the first extractor whose
`can_handle` returns True. So the cheap path always wins when it can, and the
expensive path runs only when the cheap one honestly declines.

`can_handle` MUST BE HONEST. A pdf_text_extractor that returns True for a
scanned PDF and then produces 12 characters of garbage means OCR never runs and
the document silently fails the quality gate. Cheap check, honest answer.

WHAT EVERY EXTRACTOR OWES THE REST OF THE PIPELINE:
  - Structure preserved as TextBlocks (headings stay headings).
  - Reading order correct in `order`.
  - Boilerplate stripped, content never stripped.
  - Unicode NFC-normalized, mojibake fixed.
  - ExtractionError rather than an empty "successful" document.
"""
