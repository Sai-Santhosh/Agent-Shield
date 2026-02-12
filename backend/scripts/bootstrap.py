#!/usr/bin/env python3
"""
Bootstrap script: create demo tenant, admin API key, and starter policy.
Run: docker compose exec api python -m scripts.bootstrap
Or: cd backend && python -m scripts.bootstrap (with DATABASE_URL set)
"""
import asyncio
import os

from sqlalchemy import select

from app.core.config import settings
from app.core.security import generate_api_key, hash_api_key
from app.db.init_db import init_db
from app.db.models import ApiKey, Policy, Tenant
from app.db.session import async_session

STARTER_POLICY = {
    "rules": [
        {
            "name": "deny-dangerous-iam",
            "effect": "DENY",
            "reason": "Block high-risk IAM mutations by default",
            "match": {
                "equals": {"action_type": "aws_api"},
                "in": {"aws_service": ["iam", "organizations", "sso", "sts"]},
                "glob": {"aws_operation": "*AccessKey*"},
            },
        },
        {
            "name": "require-approval-iam-core",
            "effect": "REQUIRE_APPROVAL",
            "reason": "Require approval for IAM/org changes",
            "match": {
                "equals": {"action_type": "aws_api"},
                "in": {"aws_service": ["iam", "organizations", "sso", "sts"]},
            },
        },
        {
            "name": "require-approval-sensitive-tools",
            "effect": "REQUIRE_APPROVAL",
            "reason": "Sensitive tools need human approval",
            "match": {
                "equals": {"action_type": "tool_call"},
                "in": {
                    "tool_name": ["shell", "bash", "terminal", "python_repl", "codegen", "sql"]
                },
            },
        },
    ]
}


async def main() -> None:
    await init_db()

    tenant_name = os.environ.get("TENANT_NAME", "demo-tenant")

    async with async_session() as session:
        result = await session.execute(select(Tenant).where(Tenant.name == tenant_name))
        t = result.scalar_one_or_none()
        if not t:
            t = Tenant(name=tenant_name)
            session.add(t)
            await session.commit()
            await session.refresh(t)

        raw = generate_api_key(settings.API_KEY_PREFIX)
        ak = ApiKey(
            tenant_id=t.id,
            name="admin",
            key_hash=hash_api_key(raw),
            scopes=["admin"],
            is_active=True,
        )
        session.add(ak)

        result = await session.execute(
            select(Policy).where(
                Policy.tenant_id == t.id,
                Policy.name == "starter",
            )
        )
        p = result.scalar_one_or_none()
        if not p:
            p = Policy(
                tenant_id=t.id,
                name="starter",
                enabled=True,
                dsl=STARTER_POLICY,
                version=1,
            )
            session.add(p)

        await session.commit()
        await session.refresh(ak)
        await session.refresh(p)

        print("\n" + "=" * 50)
        print("AgentShield Bootstrap Complete")
        print("=" * 50)
        print(f"Tenant:     {t.name} ({t.id})")
        print(f"Admin Key:  {raw}")
        print(f"Policy:     {p.name} (v{p.version})")
        print("=" * 50)
        print("\nSave the API key - it is shown only once.\n")


if __name__ == "__main__":
    asyncio.run(main())
