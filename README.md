# AgentShield — AI Agent Security Gateway

Production-grade API that gates agent actions: LangChain tool calls, AWS IAM mutations, and code generation. Intercepts, evaluates risk, applies policy-as-code, and supports human-in-the-loop approvals with full audit logging.

## Features

| Feature | Description |
|---------|-------------|
| **Evaluate** | `POST /v1/evaluate` — Intercept any agent action, compute risk, apply policies, return `ALLOW` / `DENY` / `REQUIRE_APPROVAL` |
| **Policy DSL** | JSON rules with `equals`, `in`, `glob` matching. Effects: `DENY` > `REQUIRE_APPROVAL` > `ALLOW` |
| **Risk Scoring** | Detects dangerous IAM ops, shell patterns, secret material in codegen/tool args |
| **Approval Workflow** | Create approvals, approve/deny with comments, optional sync wait |
| **Idempotency** | Safe retries from agents via `Idempotency-Key` header |
| **Audit Log** | Immutable event trail of all evaluations |
| **Multi-tenant** | Tenants + scoped API keys |

## Quick Start

### 1. Copy env and start

```bash
cd agent-shield
cp .env.example .env
docker compose up --build
```

### 2. Bootstrap tenant + admin key

```bash
docker compose exec api python -m scripts.bootstrap
```

Save the printed `Admin Key` — it is shown only once.

### 3. Test evaluate

```bash
export KEY="ash_live_..."   # From bootstrap

curl -s http://localhost:8080/v1/evaluate \
  -H "X-Api-Key: $KEY" \
  -H "Idempotency-Key: demo-1" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "tool_call",
    "actor": "user-1",
    "agent": "agent-1",
    "tool_name": "shell",
    "tool_args": {"command": "rm -rf /"},
    "context": {}
  }' | jq
```

### 4. Approve (when decision is REQUIRE_APPROVAL)

```bash
# Get approval_id from the evaluate response, then:
curl -s -X POST "http://localhost:8080/v1/approvals/<APPROVAL_ID>/approve" \
  -H "X-Api-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"approver": "admin", "comment": "Reviewed and approved"}' | jq
```

## Integrations

### LangChain

```python
from app.integrations.langchain_guard import AgentShieldClient, guard_tool

guard = AgentShieldClient("http://localhost:8080", "ash_live_...")
safe_shell = guard_tool(guard, "shell", shell_tool, actor="user-1", agent="my-agent")
# Use safe_shell in your LangChain agent instead of shell_tool
```

### AWS boto3 (e.g. IAM)

```python
import boto3
from app.integrations.aws_guard import GuardedBoto3Client

iam = boto3.client("iam")
guard = GuardedBoto3Client(iam, "http://localhost:8080", "ash_live_...", actor="agent-1")
# All IAM calls go through evaluate first
guard.create_user(UserName="test")  # Blocked or approved by policy
```

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/evaluate` | POST | Evaluate agent action |
| `/v1/approvals/{id}` | GET | Get approval status |
| `/v1/approvals/{id}/approve` | POST | Approve (body: `{approver, comment}`) |
| `/v1/approvals/{id}/deny` | POST | Deny (body: `{approver, comment}`) |
| `/v1/policies` | GET | List policies |
| `/v1/policies` | PUT | Upsert policy (body: `{name, enabled, dsl}`) |
| `/v1/policies/{id}/toggle` | POST | Enable/disable (?enabled=true) |
| `/v1/audit` | GET | List audit log (?limit=50) |
| `/v1/tenants` | POST | Create tenant (admin + X-Bootstrap-Secret) |
| `/v1/tenants/{id}/api-keys` | POST | Create API key (admin) |

## Policy DSL

```json
{
  "rules": [
    {
      "name": "deny-iam-access-keys",
      "effect": "DENY",
      "reason": "IAM access key creation blocked",
      "match": {
        "equals": {"action_type": "aws_api"},
        "in": {"aws_service": ["iam"]},
        "glob": {"aws_operation": "*AccessKey*"}
      }
    },
    {
      "name": "require-approval-shell",
      "effect": "REQUIRE_APPROVAL",
      "reason": "Shell commands need approval",
      "match": {
        "equals": {"action_type": "tool_call"},
        "in": {"tool_name": ["shell", "bash", "terminal"]}
      }
    }
  ]
}
```

- **equals**: field must equal value
- **in**: field must be in list
- **glob**: field must match fnmatch pattern

## Project Structure

```
agent-shield/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── core/       # config, logging, security, idempotency
│   │   ├── db/         # models, session, init
│   │   ├── services/   # policy_engine, risk, approvals
│   │   ├── api/        # routes, schemas, endpoints
│   │   └── integrations/  # langchain_guard, aws_guard
│   ├── scripts/
│   │   └── bootstrap.py
│   └── tests/
└── README.md
```

## Tests

| Command | Description |
|---------|-------------|
| `pytest tests/test_policy_engine.py tests/test_risk.py` | Unit tests (no DB) |
| `docker compose run --rm api pytest /app/tests/ -v` | Full integration (in Docker) |

```bash
# Unit tests only (no DB, always works)
cd backend && python -m pytest tests/test_policy_engine.py tests/test_risk.py tests/test_evaluate_idempotency.py -v

# Full integration (Docker required)
docker compose up -d db redis
docker compose run --rm -e INTEGRATION_USE_LOCAL_DB=1 -e DATABASE_URL=postgresql+asyncpg://agentshield:agentshield@db:5432/agentshield api python -m pytest /app/tests/ -v
```

## Development

```bash
cd backend
pip install -r requirements.txt
pytest
```
