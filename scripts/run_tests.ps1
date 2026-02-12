# AgentShield - Run tests
# Usage:
#   .\run_tests.ps1              # Unit tests only (no DB)
#   .\run_tests.ps1 -Integration # Full integration (needs Docker)
#   .\run_tests.ps1 -Local       # Integration with local Postgres (docker compose up db)

param(
    [switch]$Integration,
    [switch]$Local
)

$backend = Join-Path $PSScriptRoot "backend"
Push-Location $backend

try {
    if ($Local) {
        $env:INTEGRATION_USE_LOCAL_DB = "1"
        $env:DATABASE_URL = "postgresql+asyncpg://agentshield:agentshield@localhost:5432/agentshield"
        Write-Host "Running tests with local Postgres (ensure 'docker compose up db' is running)" -ForegroundColor Yellow
        python -m pytest tests/ -v
    } elseif ($Integration) {
        Write-Host "Running full integration tests (requires Docker)" -ForegroundColor Yellow
        python -m pytest tests/ -v
    } else {
        Write-Host "Running unit tests only (no DB required)" -ForegroundColor Cyan
        python -m pytest tests/test_policy_engine.py tests/test_risk.py tests/test_evaluate_idempotency.py -v
    }
} finally {
    Pop-Location
}
