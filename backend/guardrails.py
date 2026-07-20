import re
from typing import Dict, Any

# Security patterns for input prompt injection & malicious commands
PROMPT_INJECTION_PATTERNS = [
    re.compile(r'ignore\s+(?:all\s+)?previous\s+instructions', re.IGNORECASE),
    re.compile(r'system\s+override', re.IGNORECASE),
    re.compile(r'you\s+are\s+now\s+DAN', re.IGNORECASE),
    re.compile(r'eval\(', re.IGNORECASE),
    re.compile(r'exec\(', re.IGNORECASE),
    re.compile(r'__import__', re.IGNORECASE),
    re.compile(r'\.\./\.\./', re.IGNORECASE)
]

def validate_input_safety(prompt: str) -> Dict[str, Any]:
    """
    Scans user/agent input prompts for malicious injection, command execution, or path traversal.
    """
    if not isinstance(prompt, str):
        return {"safe": True}

    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(prompt):
            return {
                "safe": False,
                "reason": f"Security Guardrail Violation: Detected suspicious pattern matching '{pattern.pattern}'",
                "action": "REJECT_INPUT"
            }

    return {"safe": True}

def validate_output_safety(code_or_text: str) -> Dict[str, Any]:
    """
    Scans generated model code or text outputs for malicious tags, script injections, or system exploits.
    """
    if not isinstance(code_or_text, str):
        return {"safe": True}

    # Check for dangerous script injection patterns or unsafe eval calls in output
    dangerous_keywords = ["<script>eval(", "document.cookie", "window.localStorage.clear()", "child_process"]
    for kw in dangerous_keywords:
        if kw in code_or_text:
            return {
                "safe": False,
                "reason": f"Security Guardrail Violation: Generated output contained unsafe pattern '{kw}'",
                "action": "SANITIZE_OUTPUT"
            }

    return {"safe": True}
