"""Argon2id password hashing for admin accounts.

Only hash_admin_password, verify_admin_password, and needs_rehash are
part of the public API.  No plain-text password is ever stored, logged,
or embedded in an exception message.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

from backend.app.core.config import Settings


def _make_hasher(settings: Settings) -> PasswordHasher:
    """Build a PasswordHasher configured from application settings."""

    return PasswordHasher(
        time_cost=settings.argon2_time_cost,
        memory_cost=settings.argon2_memory_cost,
        parallelism=settings.argon2_parallelism,
    )


def hash_admin_password(plain_password: str, settings: Settings) -> str:
    """Return an Argon2id PHC hash of *plain_password*.

    The returned string is safe to store in the database.
    The plain-text value is not retained after this call.
    """

    hasher = _make_hasher(settings)
    return hasher.hash(plain_password)


def verify_admin_password(plain_password: str, password_hash: str) -> bool:
    """Return True if *plain_password* matches *password_hash*.

    Always returns False on any mismatch or hash format error.
    The plain-text value is never included in raised exceptions.
    """

    # Use a disposable hasher for verification; parameters are embedded in
    # the PHC string so the hasher parameters do not matter for checking.
    hasher = PasswordHasher()
    try:
        hasher.verify(password_hash, plain_password)
        return True
    except VerifyMismatchError:
        # Correct path for a wrong password — not an error condition.
        return False
    except (VerificationError, InvalidHashError):
        # Malformed hash or internal argon2 error.
        return False


def needs_rehash(password_hash: str, settings: Settings) -> bool:
    """Return True if *password_hash* was produced with weaker parameters.

    Use this after a successful login to silently upgrade stored hashes
    when the configured Argon2id parameters have been strengthened.
    """

    hasher = _make_hasher(settings)
    return hasher.check_needs_rehash(password_hash)
