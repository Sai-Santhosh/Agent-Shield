# Run integration tests inside Docker (DB + API + tests)
# Requires: cd agent-shield && docker compose up -d db redis (or full up)
# Then: .\scripts\run_integration_tests.ps1
Set-Location (Split-Path $PSScriptRoot)
docker compose run --rm -e INTEGRATION_USE_LOCAL_DB=1 -e DATABASE_URL=postgresql+asyncpg://agentshield:agentshield@db:5432/agentshield api python -m pytest /app/tests/ -v
