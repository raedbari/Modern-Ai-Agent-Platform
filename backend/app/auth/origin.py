"""Strict canonicalization and comparison for browser Origin values."""

from __future__ import annotations

from ipaddress import ip_address
from urllib.parse import urlsplit


def normalize_origin(raw_origin: str | None) -> str | None:
    """Return one canonical HTTP(S) origin or ``None`` when malformed.

    Paths, queries, fragments, credentials, wildcards, control characters,
    and opaque ``null`` origins are rejected rather than silently discarded.
    Default ports are removed because they identify the same web origin.
    """

    if raw_origin is None:
        return None
    candidate = raw_origin.strip()
    if not candidate or candidate.casefold() == "null":
        return None
    if any(ord(char) < 0x20 or char.isspace() for char in candidate):
        return None
    if "*" in candidate:
        return None

    try:
        parsed = urlsplit(candidate)
        scheme = parsed.scheme.casefold()
        if scheme not in {"http", "https"}:
            return None
        if parsed.username is not None or parsed.password is not None:
            return None
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            return None
        if parsed.hostname is None:
            return None

        raw_host = parsed.hostname.rstrip(".")
        if not raw_host:
            return None
        try:
            host = str(ip_address(raw_host))
        except ValueError:
            host = raw_host.encode("idna").decode("ascii").casefold()
        port = parsed.port
    except (UnicodeError, ValueError):
        return None

    if ":" in host:
        host = f"[{host}]"
    if (scheme == "http" and port == 80) or (
        scheme == "https" and port == 443
    ):
        port = None
    port_suffix = f":{port}" if port is not None else ""
    return f"{scheme}://{host}{port_suffix}"


def is_development_origin_allowed(
    normalized_origin: str | None,
    environment: str,
) -> bool:
    """Allow only exact loopback hosts in development and test."""

    if environment not in {"development", "test"}:
        return False
    normalized = normalize_origin(normalized_origin)
    if normalized is None:
        return False
    parsed = urlsplit(normalized)
    return parsed.hostname in {"localhost", "127.0.0.1", "::1"}
