"""Create the first customer resources from a trusted terminal."""

from __future__ import annotations

import argparse
import asyncio

from backend.app.db.base import AsyncSessionLocal
from backend.app.operations.customer_bootstrap import (
    BootstrapConflictError,
    bootstrap_customer,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create or resolve a tenant and agent, then issue one API key. "
            "Run Alembic migrations first."
        )
    )
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--tenant-name", required=True)
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--agent-name", required=True)
    parser.add_argument("--system-prompt")
    parser.add_argument(
        "--knowledge-mode",
        choices=("required", "preferred", "disabled"),
        default="required",
    )
    parser.add_argument("--fallback-message")
    parser.add_argument(
        "--no-handoff",
        action="store_true",
        help="Do not request human handoff when required knowledge is absent.",
    )
    parser.add_argument("--key-name", default="local-server")
    parser.add_argument(
        "--rotate-key",
        action="store_true",
        help="Revoke active keys with the same name before issuing a new one.",
    )
    return parser


async def _run(args: argparse.Namespace) -> int:
    async with AsyncSessionLocal() as session:
        try:
            result = await bootstrap_customer(
                session,
                tenant_id=args.tenant_id,
                tenant_name=args.tenant_name,
                agent_id=args.agent_id,
                agent_name=args.agent_name,
                system_prompt=args.system_prompt,
                key_name=args.key_name,
                knowledge_mode=args.knowledge_mode,
                fallback_message=args.fallback_message,
                handoff_enabled=not args.no_handoff,
                rotate_key=args.rotate_key,
            )
            await session.commit()
        except BootstrapConflictError as exc:
            await session.rollback()
            print(f"Bootstrap refused: {exc}")
            return 2
        except Exception:
            await session.rollback()
            raise

    print(f"Tenant ID: {result.tenant_id}")
    print(f"Agent ID:  {result.agent_id}")
    print(f"API key:   {result.api_key}")
    print("Store this key securely. It cannot be shown again.")
    return 0


def main() -> int:
    """CLI entry point."""

    return asyncio.run(_run(_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
