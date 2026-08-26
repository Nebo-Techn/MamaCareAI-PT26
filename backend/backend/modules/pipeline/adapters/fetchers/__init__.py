"""
Fetchers — one per source type (PDF 3.1).

RULES THAT APPLY TO EVERY FETCHER IN THIS PACKAGE, NOT JUST THE WEB ONE:

  1. TIMEOUT on every request. No exceptions. A hung socket holds a worker slot
     until the pod is killed.
  2. MAX SIZE, enforced while streaming — check as you read, not after. Reading
     a 4GB response into memory to then reject it has already OOM-killed the
     worker.
  3. IDENTIFY YOURSELF with the configured User-Agent, including a contact
     address. An operator who wants us to slow down should be able to reach us
     instead of just blocking us.
  4. RATE LIMIT per domain. Hammering a ministry of health website is both
     rude and the fastest way to get the project's IP banned from a source we
     genuinely need.
  5. RETRYABLE vs PERMANENT: 5xx/timeout -> FetchError (retryable);
     404/403 -> PermanentError. Getting this backwards means either infinite
     retries on a dead link, or giving up on a source that was briefly down.
"""
