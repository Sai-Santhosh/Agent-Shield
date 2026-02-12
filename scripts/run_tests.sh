#!/bin/bash
# AgentShield - Run tests
# Usage:
#   ./run_tests.sh              # Unit tests only
#   ./run_tests.sh integration  # Full integration (needs Docker)
#   ./run_tests.sh local        # Integration with local Postgres

set -e
cd "$(dirname "$0")/../backend"

case "${1:-}" in
  integration)
    echo "Running full integration tests (requires Docker)..."
    python -m pytest tests/ -v
    ;;
  local)
    export INTEGRATION_USE_LOCAL_DB=1
    export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://agentshield:agentshield@localhost:5432/agentshield}"
    echo "Running tests with local Postgres (ensure 'docker compose up db' is running)..."
    python -m pytest tests/ -v
    ;;
  *)
    echo "Running unit tests only (no DB required)..."
    python -m pytest tests/test_policy_engine.py tests/test_risk.py tests/test_evaluate_idempotency.py -v
    ;;
esac
