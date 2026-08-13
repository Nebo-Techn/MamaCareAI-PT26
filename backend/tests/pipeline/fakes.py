"""
In-memory fakes for every port.

THIS FILE IS WHY THE PORTS LAYER EARNS ITS KEEP.
With these, every stage test runs with no network, no database, no API key, no
model download, and no GPU — in milliseconds. Write these EARLY, before the
real adapters. They are what make the stages testable while the real adapters
are still being built, so two trainees can work on a stage and its adapter in
parallel without blocking each other.

FAKES, NOT MOCKS. A fake is a real working implementation with a simple
backing store (a dict, a list). A mock asserts on calls. Prefer fakes: they let
tests assert on OUTCOMES ("the resource ended up PUBLISHED") rather than on
INTERACTIONS ("save was called twice"). Interaction tests break every time you
refactor, even when the behaviour is still correct — and then people stop
trusting the test suite.

THE ONE RULE: a fake must honour its port's contract exactly. A fake translator
that returns a different number of results than it was given makes a broken
stage pass its tests, which is worse than having no test at all.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# TODO (junior dev): implement one fake per port.
#
# FakeResourceRepository(ResourceRepository)
#   dict[str, Resource]
#   [ ] `save` MUST simulate the conditional update: track a version per
#       resource and raise InvalidStateTransition on a stale write. Without
#       that, the concurrency behaviour the real repository implements is
#       never exercised by any test.
#
# FakeDocumentRepository / FakeVersionRepository / FakeReviewRepository
#   [ ] FakeVersionRepository is APPEND-ONLY, like the real one, and assigns
#       version_number itself.
#
# FakeObjectStore(ObjectStore)
#   dict[str, bytes]
#
# FakeJobQueue(JobQueue)
#   dict[stage, list[Job]] + a dead_letter list
#   [ ] Expose the lists so tests can assert "a 'translate' job was published"
#       and "nothing was dead-lettered".
#
# FakeSearchIndex(SearchIndex)
#   dict[resource_id, IndexedResource]; `search` can be a naive substring scan.
#
# FakeLanguageDetector(LanguageDetector)
#   [ ] Constructor takes the language and confidence to return, so a test can
#       set up the low-confidence path in one line.
#
# FakeTranslator(Translator)
#   [ ] Returns "[sw] " + text. Same length, same order — honour the contract.
#   [ ] Add a `fail_on` option so a test can simulate a provider failure and
#       verify the retry/dead-letter behaviour in stages/base.py.
#
# FakeFetcher(SourceFetcher) / FakeExtractor(ContentExtractor)
#   [ ] Constructor takes canned content to return.
#
# --- Test data builders ---
#
# make_resource(**overrides) -> Resource
# make_document(blocks=..., **overrides) -> NormalizedDocument
#   [ ] Sensible defaults, overridable per field. Without builders every test
#       constructs a 12-field Resource by hand, and adding a field to the model
#       means editing forty tests. With them, it means editing one function.
# ---------------------------------------------------------------------------
