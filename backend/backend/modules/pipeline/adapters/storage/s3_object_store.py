"""
S3 object store — the production backend (PDF 3.5: "S3 or equivalent").

Swap in by setting PIPELINE_OBJECT_STORE_BACKEND=s3. No stage changes.

Works with any S3-compatible service, which matters on a zero-budget project:
MinIO (self-hosted), Cloudflare R2 (no egress fees), or Backblaze B2 are all
drop-in via `endpoint_url`. Do not hardcode AWS.
"""

from __future__ import annotations

from ...ports.object_store import ObjectStore


class S3ObjectStore(ObjectStore):
    """Stores objects in an S3-compatible bucket."""

    def __init__(
        self,
        *,
        bucket: str,
        region: str | None = None,
        endpoint_url: str | None = None,  # set for MinIO / R2 / B2
        prefix: str = "",
    ) -> None:
        # TODO: create ONE boto3 client here and reuse it — client creation is
        # surprisingly expensive and thread-safe reuse is the documented pattern.
        self._bucket = bucket
        self._prefix = prefix

    def put(self, key: str, content: bytes, *, content_type: str) -> str:
        """TODO:
        [ ] put_object with ContentType set — it matters when a human later
            opens the object from a browser or a console.
        [ ] Use multipart upload above ~100MB. Large health-guideline PDFs
            and audio files will exceed the single-request practical limit.
        [ ] Enable SERVER-SIDE ENCRYPTION (SSE-S3 at minimum). PDF section 4
            calls for access control on raw content, and this is the cheapest
            half of it.
        [ ] Map ClientError to our types: throttling/5xx -> TransientError,
            AccessDenied/NoSuchBucket -> PermanentError with a message that
            names the bucket.
        """
        raise NotImplementedError

    def get(self, key: str) -> bytes:
        """TODO: get_object; NoSuchKey -> PermanentError, throttling -> TransientError."""
        raise NotImplementedError

    def exists(self, key: str) -> bool:
        """TODO: head_object; 404 -> False. Do NOT use list_objects for this —
        a HEAD is one cheap call, a LIST is a paginated scan."""
        raise NotImplementedError
