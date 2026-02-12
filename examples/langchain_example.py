"""
Example: Wrap a LangChain tool with AgentShield.
Run AgentShield API first (docker compose up), then bootstrap, then run this.
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.integrations.langchain_guard import AgentShieldClient, guard_tool

BASE_URL = "http://localhost:8080"
API_KEY = "ash_live_..."  # Replace with key from bootstrap


def fake_shell_tool(command: str) -> str:
    """Simulated shell tool - in real usage this would exec."""
    return f"Executed: {command}"


if __name__ == "__main__":
    guard = AgentShieldClient(BASE_URL, API_KEY)
    safe_shell = guard_tool(
        guard, "shell", fake_shell_tool, actor="user-1", agent="demo-agent"
    )

    # This will be evaluated by AgentShield - likely REQUIRE_APPROVAL or DENY
    try:
        result = safe_shell(command="ls -la")
        print("Result:", result)
    except RuntimeError as e:
        print("Blocked/Approval required:", e)
