"""Tests for API-key credential primitives."""

from backend.app.auth.api_keys import (
    issue_api_key,
    parse_api_key,
    verify_api_key_secret,
)


def test_issued_key_can_be_parsed_and_verified() -> None:
    issued = issue_api_key()

    parsed = parse_api_key(issued.raw_key)

    assert parsed is not None
    key_id, secret = parsed
    assert key_id == issued.key_id
    assert verify_api_key_secret(secret, issued.key_digest)


def test_raw_key_is_not_exposed_by_repr() -> None:
    issued = issue_api_key()

    assert issued.raw_key not in repr(issued)


def test_malformed_or_modified_keys_are_rejected() -> None:
    issued = issue_api_key()
    parsed = parse_api_key(issued.raw_key)

    assert parsed is not None
    _, secret = parsed
    assert parse_api_key("invalid") is None
    assert parse_api_key("maap_missing-separator") is None
    assert not verify_api_key_secret(
        f"{secret}-modified",
        issued.key_digest,
    )