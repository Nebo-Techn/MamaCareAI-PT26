from __future__ import annotations

import os
from pathlib import Path, PureWindowsPath
from tempfile import NamedTemporaryFile

from ...domain.errors import PermanentError
from ...ports.object_store import ObjectStore


class FilesystemObjectStore(ObjectStore):
    def __init__(self, *, root: Path) -> None:
        self._root = root.expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def put(self, key: str, content: bytes, *, content_type: str) -> str:
        if not isinstance(content, bytes):
            raise PermanentError("object-store content must be bytes")

        path = self._path_for_key(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(dir=path.parent, delete=False) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(content)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
        return key

    def get(self, key: str) -> bytes:
        path = self._path_for_key(key)
        try:
            return path.read_bytes()
        except FileNotFoundError as error:
            raise PermanentError(f"object not found: {key}") from error

    def exists(self, key: str) -> bool:
        try:
            return self._path_for_key(key).is_file()
        except (OSError, PermanentError):
            return False

    def _path_for_key(self, key: str) -> Path:
        if not isinstance(key, str) or not key:
            raise PermanentError("object key must be a non-empty relative path")

        key_path = Path(key)
        windows_key_path = PureWindowsPath(key)
        if (
            key_path.is_absolute()
            or windows_key_path.is_absolute()
            or windows_key_path.drive
            or "\\" in key
            or any(segment in {"", ".", ".."} for segment in key.split("/"))
        ):
            raise PermanentError(f"unsafe object key: {key!r}")

        path = (self._root / key_path).resolve()
        try:
            path.relative_to(self._root)
        except ValueError as error:
            raise PermanentError(f"unsafe object key: {key!r}") from error
        return path
