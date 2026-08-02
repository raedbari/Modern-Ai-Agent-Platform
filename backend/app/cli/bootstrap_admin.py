"""Create the first super_admin account from a trusted terminal.

Usage::

    python -m backend.app.cli.bootstrap_admin --username admin

The password is read from a hidden terminal prompt. Automation may pass it
through standard input with ``--password-stdin``; it is never accepted as a
command-line argument.

Run Alembic migrations before invoking this script.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
import uuid

from backend.app.db.models import AdminUser
from backend.app.operations.admin_auth_ops import (
    WeakPasswordError,
    _validate_password_strength,
)


async def _super_admin_exists(session) -> bool:
    """Return True if at least one super_admin row exists."""
    from sqlalchemy import select

    row = await session.scalar(
        select(AdminUser).where(AdminUser.role == "super_admin").limit(1)
    )
    return row is not None


async def _run(args: argparse.Namespace) -> int:
    from backend.app.core.config import get_settings
    from backend.app.auth.admin_password import hash_admin_password
    from backend.app.db.base import AsyncSessionLocal

    settings = get_settings()

    # --- validate password strength before touching the database ----------
    try:
        _validate_password_strength(args.password)
    except WeakPasswordError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    async with AsyncSessionLocal() as session:
        exists = await _super_admin_exists(session)

        if exists and not args.force:
            print(
                "Error: a super_admin account already exists. "
                "Use --force to overwrite.",
                file=sys.stderr,
            )
            return 2

        if exists and args.force:
            # Deactivate the existing super_admin and replace with new one.
            from sqlalchemy import select, update

            await session.execute(
                update(AdminUser)
                .where(AdminUser.role == "super_admin")
                .values(is_active=False)
            )
            print("Existing super_admin account deactivated.")

        hashed = hash_admin_password(args.password, settings)
        admin = AdminUser(
            id=str(uuid.uuid4()),
            username=args.username,
            hashed_password=hashed,
            role="super_admin",
            is_active=True,
        )
        session.add(admin)

        try:
            await session.commit()
        except Exception as exc:
            await session.rollback()
            print(f"Error: could not create admin account: {exc}", file=sys.stderr)
            return 3

    print(f"super_admin '{args.username}' created successfully.")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create the first super_admin admin account. "
            "Run Alembic migrations first."
        )
    )
    parser.add_argument(
        "--username",
        required=True,
        help="Admin username (max 64 chars)",
    )
    parser.add_argument(
        "--password-stdin",
        action="store_true",
        help="Read the password from standard input instead of a hidden prompt.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Deactivate existing super_admin and create a new one.",
    )
    return parser


def main() -> int:
    """CLI entry point."""
    args = _parser().parse_args()
    if args.password_stdin:
        args.password = sys.stdin.readline().rstrip("\r\n")
    else:
        args.password = getpass.getpass("Admin password: ")
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
