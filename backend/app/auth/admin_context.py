"""Trusted authorization context for authenticated admin operators."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class AdminContext:
    """Admin identity and role resolved by the JWT authentication layer."""

    admin_id: str
    username: str
    role: Literal["super_admin", "operator", "auditor"]
