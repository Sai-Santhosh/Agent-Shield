"""Risk scoring tests."""
from app.services.risk import score_risk


def test_dangerous_shell_command():
    score, signals = score_risk(
        "tool_call",
        {"tool_name": "shell", "tool_args": {"command": "rm -rf /"}},
    )
    assert score > 50
    assert "dangerous_pattern" in str(signals) or "sensitive_tool" in str(signals)


def test_iam_create_access_key():
    score, signals = score_risk(
        "aws_api",
        {"aws_service": "iam", "aws_operation": "CreateAccessKey", "params": {}},
    )
    assert score >= 40
    assert "dangerous_operation" in str(signals) or "high_value_service" in str(signals)


def test_low_risk_action():
    score, signals = score_risk(
        "tool_call",
        {"tool_name": "search", "tool_args": {"query": "hello"}},
    )
    assert score < 50
