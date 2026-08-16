"""Object storage port interface for the Knowledge Platform.

Defines the abstract boundary between the service layer and any concrete
object storage backend (S3, GCS, Azure Blob, local filesystem, in-memory).

The service layer depends only on ``ObjectStoragePort``; infrastructure
adapters implement the protocol without the domain layer knowing anything
about the underlying storage technology.

Design notes:
- ``ObjectStoragePort`` is a ``typing.Protocol`` so adapters do not need to
  inherit from a base class — structural subtyping is sufficient.
- All methods are async because cloud storage calls are inherently I/O-bound.
- ``put`` returns the storage key so callers can persist it for later retrieval.
- ``get`` raises ``KeyError`` when the key does not exist, consistent with
  Python's built-in mapping contract.
- ``delete`` is a no-op when the key is absent — callers must never need to
  check existence before deleting.
- No framework imports, no infrastructure imports, no library imports.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ObjectStoragePort(Protocol):
    """Abstract contract for an object storage backend.

    Any object that implements these four async methods satisfies the port.
    Infrastructure adapters (S3, GCS, local, null) fulfil this contract
    without inheriting from this class.

    All keys are opaque strings — the caller is responsible for generating
    a collision-free, tenant-scoped key before calling ``put``.
    """

    async def put(
        self,
        key: str,
        content: bytes,
        content_type: str,
    ) -> str:
        """Store ``content`` under ``key``.

        Args:
            key:          Opaque, globally unique storage key.  Must not be
                          empty.  Callers are responsible for namespacing
                          keys by tenant to enforce isolation.
            content:      Raw bytes to store.  May be empty (zero-byte file).
            content_type: MIME type string (e.g. ``"application/pdf"``).
                          Passed through to the storage backend for correct
                          HTTP ``Content-Type`` headers on retrieval.

        Returns:
            The ``key`` as stored, identical to the input ``key`` in the
            common case.  Adapters that normalise or transform keys must
            return the canonical form that ``get`` and ``delete`` accept.
        """
        ...

    async def get(self, key: str) -> bytes:
        """Retrieve the raw bytes stored under ``key``.

        Args:
            key: The storage key previously returned by ``put``.

        Returns:
            The raw bytes that were stored.

        Raises:
            KeyError: When no object exists for the given ``key``.
        """
        ...

    async def delete(self, key: str) -> None:
        """Remove the object stored under ``key``.

        This method is idempotent: if the key does not exist the call
        succeeds silently.  Callers must never rely on this method raising
        an exception to detect missing keys.

        Args:
            key: The storage key to remove.
        """
        ...

    async def exists(self, key: str) -> bool:
        """Return whether an object exists for the given ``key``.

        Prefer this over ``get`` when only existence needs to be verified,
        to avoid loading potentially large payloads.

        Args:
            key: The storage key to probe.

        Returns:
            ``True`` if an object exists for ``key``, ``False`` otherwise.
        """
        ...
