"""Tests for the Argon2id admin password hashing module."""

from __future__ import annotations

import pytest

from backend.app.auth.admin_password import (
    hash_admin_password,
    needs_rehash,
    verify_admin_password,
)
from backend.app.core.config import Settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _default_settings() -> Settings:
    """Return a minimal Settings instance with default Argon2id parameters."""

    return Settings(
        # Keep memory low so tests run quickly while still being valid.
        argon2_time_cost=1,
        argon2_memory_cost=8192,
        argon2_parallelism=1,
        _env_file=None,
    )


def _weak_settings() -> Settings:
    """Return settings with parameters below the defaults, to trigger rehash."""

    return Settings(
        argon2_time_cost=1,
        argon2_memory_cost=8192,
        argon2_parallelism=1,
        _env_file=None,
    )


def _strong_settings() -> Settings:
    """Return settings with higher parameters than _weak_settings."""

    return Settings(
        argon2_time_cost=2,
        argon2_memory_cost=16384,
        argon2_parallelism=1,
        _env_file=None,
    )


# ---------------------------------------------------------------------------
# PHC string format
# ---------------------------------------------------------------------------

def test_hash_output_starts_with_argon2id_prefix() -> None:
    """Produced hashes must use the Argon2id variant, not Argon2i or Argon2d."""

    password_hash = hash_admin_password("CorrectHorseBatteryStaple1!", _default_settings())

    assert password_hash.startswith("$argon2id$")


# ---------------------------------------------------------------------------
# Correct verification
# ---------------------------------------------------------------------------

def test_correct_password_verifies_successfully() -> None:
    plain = "MySecurePassword99@"
    password_hash = hash_admin_password(plain, _default_settings())

    assert verify_admin_password(plain, password_hash) is True


# ---------------------------------------------------------------------------
# Wrong password
# ---------------------------------------------------------------------------

def test_incorrect_password_fails_verification() -> None:
    plain = "MySecurePassword99@"
    password_hash = hash_admin_password(plain, _default_settings())

    assert verify_admin_password("WrongPassword!", password_hash) is False


def test_empty_password_fails_verification() -> None:
    plain = "MySecurePassword99@"
    password_hash = hash_admin_password(plain, _default_settings())

    assert verify_admin_password("", password_hash) is False


# ---------------------------------------------------------------------------
# Non-determinism (random salt)
# ---------------------------------------------------------------------------

def test_two_hashes_of_same_password_are_different() -> None:
    """Argon2id uses a random salt, so the same password produces distinct hashes."""

    plain = "SamePlainText123!"
    settings = _default_settings()
    hash_a = hash_admin_password(plain, settings)
    hash_b = hash_admin_password(plain, settings)

    assert hash_a != hash_b


# ---------------------------------------------------------------------------
# needs_rehash
# ---------------------------------------------------------------------------

def test_needs_rehash_returns_false_for_current_parameters() -> None:
    settings = _default_settings()
    password_hash = hash_admin_password("AnyPassword1!", settings)

    # A hash produced with the same settings should not need rehashing.
    assert needs_rehash(password_hash, settings) is False


def test_needs_rehash_returns_true_when_parameters_are_strengthened() -> None:
    # Hash with weak parameters.
    weak_hash = hash_admin_password("AnyPassword1!", _weak_settings())

    # Check against stronger parameters.
    assert needs_rehash(weak_hash, _strong_settings()) is True


# ---------------------------------------------------------------------------
# Security: no plaintext in exceptions
# ---------------------------------------------------------------------------

def test_verify_with_malformed_hash_does_not_raise() -> None:
    """A garbage hash value must never cause an unhandled exception."""

    result = verify_admin_password("SomePassword1!", "not-a-valid-argon2-hash")

    assert result is False


def test_exception_message_does_not_contain_plain_password() -> None:
    """verify_admin_password must not propagate plain-text passwords."""

    plain = "SuperSecretValue99!"
    try:
        verify_admin_password(plain, "$argon2id$v=19$m=8192,t=1,p=1$invalidsalt$invalidhash")
    except Exception as exc:
        assert plain not in str(exc), (
            "Plain-text password must never appear in exception messages"
        )
