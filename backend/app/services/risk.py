"""Risk scoring for agent actions (tool calls, AWS API, codegen)."""
import re
from typing import Any

# High-risk IAM operations that warrant blocking or approval
DANGEROUS_IAM_OPS = {
    "CreateAccessKey",
    "PutUserPolicy",
    "PutRolePolicy",
    "AttachUserPolicy",
    "AttachRolePolicy",
    "CreatePolicyVersion",
    "SetDefaultPolicyVersion",
    "UpdateAssumeRolePolicy",
    "CreateUser",
    "CreateRole",
    "UpdateLoginProfile",
    "DeleteUser",
    "DeleteRole",
    "DeleteAccessKey",
}

# Shell patterns that indicate potentially malicious commands
DANGEROUS_SHELL_PATTERNS = [
    r"\brm\s+-rf\b",
    r"\bcurl\b.*\|\s*sh\b",
    r"\bwget\b.*\|\s*sh\b",
    r"\bchmod\s+\+x\b",
    r"\b(bash|sh)\s+-c\b",
    r"\bmkfs\.(ext4|xfs)\b",
]

# Sensitive tools that should trigger approval
SENSITIVE_TOOLS = {"shell", "bash", "terminal", "python_repl", "sql", "codegen", "execute_code"}


def score_risk(action_type: str, payload: dict[str, Any]) -> tuple[int, list[str]]:
    """
    Compute risk score (0-100) and list of signals.
    Higher score = higher risk = more likely to require approval or denial.
    """
    score = 0
    signals: list[str] = []

    if action_type == "aws_api":
        svc = (payload.get("aws_service") or "").lower()
        op = payload.get("aws_operation") or ""
        params = payload.get("params") or {}

        if svc in {"iam", "organizations", "sso", "sts"}:
            score += 30
            signals.append(f"high_value_service:{svc}")

        if op in DANGEROUS_IAM_OPS:
            score += 40
            signals.append(f"dangerous_operation:{op}")

        doc = str(params)
        if "*" in doc:
            score += 15
            signals.append("wildcard_detected")

    if action_type in {"tool_call", "codegen"}:
        tool = (payload.get("tool_name") or "").lower()
        args = payload.get("tool_args") or {}
        text = str(args.get("command") or args.get("code") or args.get("input") or "")

        if tool in SENSITIVE_TOOLS:
            score += 25
            signals.append(f"sensitive_tool:{tool}")

        for pat in DANGEROUS_SHELL_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                score += 40
                signals.append(f"dangerous_pattern:{pat[:30]}")

        if "AWS_SECRET_ACCESS_KEY" in text or "BEGIN PRIVATE KEY" in text:
            score += 50
            signals.append("secret_material_detected")

    return min(score, 100), signals
