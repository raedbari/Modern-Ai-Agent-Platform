"""Tests for the ObjectStoragePort contract and NullObjectStorageAdapter.

Verifies:
- ``ObjectStoragePort`` Protocol is importable and has the expected methods.
- ``NullObjectStorageAdapter`` satisfies the ``ObjectStoragePort`` Protocol.
- put/get round-trip returns the original bytes.
- get raises ``KeyError`` for a missing key.
- exists returns ``True`` after a put.
- exists returns ``False`` before a put.
- delete removes the stored object.
- delete on a non-existent key is a no-op (no exception raised).
- clear empties the entire in-memory store.
- put raises ``ValueError`` for an empty key.
"""

from __future__ import annotations

import pytest

from backend.app.domain.ports.object_storage import ObjectStoragePort
from backend.app.infrastructure.storage.null_object_storage import (
    NullObjectStorageAdapter,
)


# ---------------------------------------------------------------------------
# Port contract
# ---------------------------------------------------------------------------


class TestObjectStoragePortContract:
    """Structural checks for the ObjectStoragePort Protocol."""

    def test_importable(self) -> None:
        assert ObjectStoragePort is not None

    def test_has_expected_methods(self) -> None:
        expected = {"put", "get", "delete", "exists"}
        assert expected <= set(dir(ObjectStoragePort))

    def test_null_adapter_satisfies_protocol(self) -> None:
        """NullObjectStorageAdapter is an instance of ObjectStoragePort."""
        adapter = NullObjectStorageAdapter()
        assert isinstance(adapter, ObjectStoragePort)


# ---------------------------------------------------------------------------
# NullObjectStorageAdapter behaviour
# ---------------------------------------------------------------------------


@pytest.fixture()
def adapter() -> NullObjectStorageAdapter:
    """A fresh NullObjectStorageAdapter for each test."""
    return NullObjectStorageAdapter()


class TestNullObjectStorageAdapterPutGet:
    @pytest.mark.asyncio
    async def test_put_returns_key(self, adapter: NullObjectStorageAdapter) -> None:
        returned_key = await adapter.put("doc/a.pdf", b"hello", "application/pdf")
        assert returned_key == "doc/a.pdf"

    @pytest.mark.asyncio
    async def test_put_get_round_trip(self, adapter: NullObjectStorageAdapter) -> None:
        content = b"PDF content bytes"
        await adapter.put("tenant1/doc1.pdf", content, "application/pdf")
        retrieved = await adapter.get("tenant1/doc1.pdf")
        assert retrieved == content

    @pytest.mark.asyncio
    async def test_put_overwrite(self, adapter: NullObjectStorageAdapter) -> None:
        """Putting a key twice stores the latest bytes."""
        await adapter.put("k", b"v1", "text/plain")
        await adapter.put("k", b"v2", "text/plain")
        assert await adapter.get("k") == b"v2"

    @pytest.mark.asyncio
    async def test_put_empty_content_is_allowed(
        self, adapter: NullObjectStorageAdapter
    ) -> None:
        """Zero-byte files are valid (empty documents, tombstones)."""
        key = await adapter.put("empty", b"", "application/octet-stream")
        assert await adapter.get(key) == b""

    @pytest.mark.asyncio
    async def test_get_missing_key_raises_key_error(
        self, adapter: NullObjectStorageAdapter
    ) -> None:
        with pytest.raises(KeyError):
            await adapter.get("does-not-exist")


class TestNullObjectStorageAdapterExists:
    @pytest.mark.asyncio
    async def test_exists_false_before_put(
        self, adapter: NullObjectStorageAdapter
    ) -> None:
        assert await adapter.exists("ghost-key") is False

    @pytest.mark.asyncio
    async def test_exists_true_after_put(
        self, adapter: NullObjectStorageAdapter
    ) -> None:
        await adapter.put("present", b"data", "application/octet-stream")
        assert await adapter.exists("present") is True

    @pytest.mark.asyncio
    async def test_exists_false_after_delete(
        self, adapter: NullObjectStorageAdapter
    ) -> None:
        await adapter.put("temp", b"data", "application/octet-stream")
        await adapter.delete("temp")
        assert await adapter.exists("temp") is False


class TestNullObjectStorageAdapterDelete:
    @pytest.mark.asyncio
    async def test_delete_removes_key(self, adapter: NullObjectStorageAdapter) -> None:
        await adapter.put("to-delete", b"bytes", "text/plain")
        await adapter.delete("to-delete")
        with pytest.raises(KeyError):
            await adapter.get("to-delete")

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key_is_noop(
        self, adapter: NullObjectStorageAdapter
    ) -> None:
        """Deleting a key that was never put must not raise."""
        await adapter.delete("never-existed")  # must not raise

    @pytest.mark.asyncio
    async def test_delete_twice_is_noop(
        self, adapter: NullObjectStorageAdapter
    ) -> None:
        """Deleting the same key twice must not raise."""
        await adapter.put("once", b"x", "text/plain")
        await adapter.delete("once")
        await adapter.delete("once")  # second delete — must not raise


class TestNullObjectStorageAdapterClear:
    @pytest.mark.asyncio
    async def test_clear_empties_store(
        self, adapter: NullObjectStorageAdapter
    ) -> None:
        await adapter.put("k1", b"a", "text/plain")
        await adapter.put("k2", b"b", "text/plain")
        adapter.clear()
        assert await adapter.exists("k1") is False
        assert await adapter.exists("k2") is False

    @pytest.mark.asyncio
    async def test_clear_on_empty_store_is_noop(
        self, adapter: NullObjectStorageAdapter
    ) -> None:
        """Clearing an already-empty store must not raise."""
        adapter.clear()  # must not raise

    @pytest.mark.asyncio
    async def test_put_after_clear_works(
        self, adapter: NullObjectStorageAdapter
    ) -> None:
        await adapter.put("before", b"data", "text/plain")
        adapter.clear()
        await adapter.put("after", b"new data", "text/plain")
        assert await adapter.get("after") == b"new data"


class TestNullObjectStorageAdapterValidation:
    @pytest.mark.asyncio
    async def test_put_empty_key_raises_value_error(
        self, adapter: NullObjectStorageAdapter
    ) -> None:
        with pytest.raises(ValueError, match="key"):
            await adapter.put("", b"data", "text/plain")
