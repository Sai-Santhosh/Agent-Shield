# AgentShield Integration Examples

1. Start AgentShield: `docker compose up --build`
2. Bootstrap: `docker compose exec api python -m scripts.bootstrap`
3. Copy the admin API key into the example scripts

## langchain_example.py

Shows how to wrap a LangChain tool with `guard_tool()` so every invocation goes through AgentShield.
