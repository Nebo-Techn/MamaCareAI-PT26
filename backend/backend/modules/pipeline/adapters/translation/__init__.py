"""
Translation adapters (PDF 3.4).

Contains the two engine options from the design doc — self-hosted NLLB-200 and
cloud MT — plus the chunker they both depend on.

PDF section 6 lists "self-hosted versus cloud translation" as an OPEN QUESTION.
Because both sit behind the `Translator` port, that question does not block
development: build with `passthrough` and `nllb` locally, and switch engines
with `PIPELINE_TRANSLATION_ENGINE` once cost and data-privacy requirements are
settled. Decide late, on evidence, at zero migration cost.
"""
