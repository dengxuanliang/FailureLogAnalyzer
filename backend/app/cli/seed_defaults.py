from __future__ import annotations

import argparse
import asyncio
import os

from app.db.session import get_async_session
from app.services.default_seed import seed_defaults


async def _run(provider: str, model: str, created_by: str) -> None:
    async with get_async_session() as db:
        report = await seed_defaults(db, provider=provider, model=model, created_by=created_by)

    def _fmt(items: list[str]) -> str:
        return ", ".join(items) if items else "(none)"

    print("Seed defaults complete")
    print(f"  templates created: {_fmt(report.created_templates)}")
    print(f"  templates skipped: {_fmt(report.skipped_templates)}")
    print(f"  strategies created: {_fmt(report.created_strategies)}")
    print(f"  strategies skipped: {_fmt(report.skipped_strategies)}")
    print(f"  rules created: {_fmt(report.created_rules)}")
    print(f"  rules skipped: {_fmt(report.skipped_rules)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed default rules, strategies, and prompt templates")
    parser.add_argument(
        "--provider",
        default=os.getenv("SEED_LLM_PROVIDER", "openai"),
        help="LLM provider name (default: openai)",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("SEED_LLM_MODEL", "gpt-4o"),
        help="LLM model name (default: gpt-4o)",
    )
    parser.add_argument(
        "--created-by",
        default=os.getenv("SEED_CREATED_BY", "bootstrap"),
        help="created_by attribution (default: bootstrap)",
    )
    args = parser.parse_args()
    asyncio.run(_run(args.provider, args.model, args.created_by))


if __name__ == "__main__":
    main()
