"""
Filesystem object store — the free MVP backend for raw artifacts.

Writes to `data/02_raw/` on local disk, which is exactly where
docs/ARCHITECTURE.md's data flow already expects raw files to land. Zero setup,
zero cost, and a trainee can open the files in Explorer to see what the
pipeline actually downloaded — genuinely useful while debugging extraction.

LIMITS, STATED HONESTLY: single-machine only. The moment there are workers on
more than one host, they no longer see each other's files and this must be
swapped for S3. That swap is one config value, because both sit behind the
`ObjectStore` port.
"""

from __future__ import annotations

from pathlib import Path

from ...ports.object_store import ObjectStore


class FilesystemObjectStore(ObjectStore):
    """Stores objects as files under a root directory."""

    def __init__(self, *, root: Path) -> None:
        # TODO: create the root directory if missing, and resolve it to an
        # absolute path once, at construction.
        self._root = root

    def put(self, key: str, content: bytes, *, content_type: str) -> str:
        """Write bytes to <root>/<key>.

        TODO (junior dev):
          [ ] VALIDATE THE KEY FIRST — reject "..", absolute paths, and drive
              letters. A key derived from remote content that escapes the root
              is a path-traversal bug that lets a fetched document overwrite
              arbitrary files. This is the security-critical line in this file.
          [ ] mkdir parents for the key's directory.
          [ ] WRITE TO A TEMP FILE, THEN os.replace() INTO PLACE. An
              interrupted direct write leaves a truncated file that looks
              complete to `exists()`, and the corruption surfaces later in
              extraction where it makes no sense.
          [ ] Return the key.
          [ ] Idempotent: rewriting the same key with the same bytes is fine
              and must not raise.
        """
        raise NotImplementedError

    def get(self, key: str) -> bytes:
        """TODO: validate the key as above, read the file, and raise a
        PermanentError (not FileNotFoundError) when it is missing — stages
        should only ever have to catch pipeline error types."""
        raise NotImplementedError

    def exists(self, key: str) -> bool:
        """TODO: validate the key, then Path.is_file(). Never raise."""
        raise NotImplementedError
