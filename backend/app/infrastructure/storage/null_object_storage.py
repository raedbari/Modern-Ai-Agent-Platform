"""Null (in-memory) adapter for the ObjectStoragePort.

Implements the ``ObjectStoragePort`` Protocol using a plain Python dict as
the backing store.  Designed for two use cases:

1. **Tests** — provides a fast, hermetic storage backend with a ``clear()``
   helper for inter-test isolation.
2. **Current production default** — the platform processes files in-memory
   today with no persistent object storage.  This adapter makes that
   behaviour explicit and swappable without changing service code.

Swapping to a real backend (S3, GCS, Azure Blob) only requires providing an
adapter that satisfies ``ObjectStoragePort``; no service code changes.
"""

from __future__ import annotations


class NullObjectStorageAdapter:
    """In-memory implementation of ``ObjectStoragePort``.

    All objects are stored in ``_store``, a plain ``dict[str, bytes]``
    keyed by the storage key supplied to ``put``.  The store lives for the
    lifetime of the adapter instance.

    Thread safety: this adapter is not thread-safe.  For testing with
    concurrent coroutines, create one instance per test or protect access
    with a lock.  In production it is used from a single async event loop,
    so the lack of a lock is acceptable.
    """

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    # ------------------------------------------------------------------
    # ObjectStoragePort implementation
    # ------------------------------------------------------------------

    async def put(
        self,
        key: str,
        content: bytes,
        content_type: str,
    ) -> str:
        """Store ``content`` in memory under ``key``.

        Args:
            key:          Opaque storage key.  Must not be empty.
            content:      Raw bytes to store.
            content_type: MIME type; accepted but not persisted by this
                          adapter (there is no HTTP layer to serve it).

        Returns:
            The ``key`` unchanged.

        Raises:
            ValueError: When ``key`` is empty.
        """
        if not key:
            raise ValueError("Storage key must not be empty.")
        self._store[key] = content
        return key

    async def get(self, key: str) -> bytes:
        """Retrieve bytes stored under ``key``.

        Args:
            key: The storage key previously returned by ``put``.

        Returns:
            The raw bytes that were stored.

        Raises:
            KeyError: When no object exists for the given ``key``.
        """
        try:
            return self._store[key]
        except KeyError:
            raise KeyError(key) from None

    async def delete(self, key: str) -> None:
        """Remove the object stored under ``key``.

        No-op when the key is absent — never raises.

        Args:
            key: The storage key to remove.
        """
        self._store.pop(key, None)

    async def exists(self, key: str) -> bool:
        """Return whether ``key`` is present in the in-memory store.

        Args:
            key: The storage key to probe.

        Returns:
            ``True`` if the key exists, ``False`` otherwise.
        """
        return key in self._store

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Empty the in-memory store.

        Intended for test teardown so that one test's stored objects do not
        leak into the next test.
        """
        self._store.clear()
