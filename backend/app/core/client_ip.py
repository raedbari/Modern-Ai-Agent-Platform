"""Resolve client IP addresses without trusting arbitrary forwarding headers."""

from __future__ import annotations

from ipaddress import ip_address, ip_network

from fastapi import Request

from backend.app.core.config import Settings


def _normalized_ip(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(ip_address(value.strip()))
    except ValueError:
        return None


def _is_trusted_proxy(value: str, settings: Settings) -> bool:
    address = ip_address(value)
    return any(
        address in ip_network(cidr, strict=False)
        for cidr in settings.trusted_proxy_cidrs
    )


def get_client_ip(request: Request, settings: Settings) -> str | None:
    """Return a verified client address.

    ``X-Forwarded-For`` is considered only when the direct peer belongs to a
    configured trusted proxy network. The chain is walked from right to left
    and the nearest untrusted address is selected.
    """

    peer = _normalized_ip(request.client.host if request.client else None)
    if peer is None:
        return None
    if not _is_trusted_proxy(peer, settings):
        return peer

    forwarded = request.headers.get("X-Forwarded-For", "")
    chain = [
        normalized
        for part in forwarded.split(",")
        if (normalized := _normalized_ip(part)) is not None
    ]
    chain.append(peer)

    for candidate in reversed(chain):
        if not _is_trusted_proxy(candidate, settings):
            return candidate
    return chain[0]
