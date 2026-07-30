"""Atomic local filesystem storage for retained source uploads."""

from __future__ import annotations

import asyncio
import hashlib
import os
from pathlib import Path
import tempfile


class StoredUploadNotFoundError(FileNotFoundError):
    """Raised without exposing a host filesystem path."""


class LocalUploadStorage:
    """Store source bytes under opaque, traversal-safe object keys."""

    def __init__(self, root: Path) -> None:
        self._root = root.expanduser().resolve()

    @staticmethod
    def object_key(tenant_id: str, document_id: str) -> str:
        """Create an opaque deterministic key without user-controlled paths."""

        tenant_hash = hashlib.sha256(
            tenant_id.encode("utf-8")
        ).hexdigest()
        document_hash = hashlib.sha256(
            document_id.encode("utf-8")
        ).hexdigest()
        return (
            f"{tenant_hash[:2]}/{tenant_hash}/"
            f"{document_hash}.source"
        )

    async def store(
        self,
        *,
        tenant_id: str,
        document_id: str,
        content: bytes,
    ) -> str:
        if not content:
            raise ValueError("Stored upload content must not be empty.")
        key = self.object_key(tenant_id, document_id)
        await asyncio.to_thread(self._atomic_write, key, content)
        return key

    async def read(self, storage_key: str) -> bytes:
        try:
            return await asyncio.to_thread(
                self._path(storage_key).read_bytes
            )
        except FileNotFoundError as exc:
            raise StoredUploadNotFoundError(
                "Stored upload is unavailable."
            ) from exc

    async def delete(self, storage_key: str) -> None:
        path = self._path(storage_key)
        try:
            await asyncio.to_thread(path.unlink)
        except FileNotFoundError:
            return

    def _atomic_write(self, storage_key: str, content: bytes) -> None:
        target = self._path(storage_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".upload-",
            dir=target.parent,
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()

    def _path(self, storage_key: str) -> Path:
        if not storage_key or "\\" in storage_key:
            raise ValueError("Invalid storage key.")
        relative = Path(storage_key)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Invalid storage key.")
        path = (self._root / relative).resolve()
        if not path.is_relative_to(self._root):
            raise ValueError("Invalid storage key.")
        return path
