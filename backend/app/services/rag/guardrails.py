import re

PII_PATTERNS = [
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
]

BLOCKLIST_PATTERNS = [
    re.compile(r"ignore\s+all\s+previous\s+instructions", re.IGNORECASE),
    re.compile(r"reveal\s+system\s+prompt", re.IGNORECASE),
    re.compile(r"exfiltrate|leak|bypass", re.IGNORECASE),
    re.compile(r"developer\s+message|hidden\s+prompt", re.IGNORECASE),
    re.compile(r"jailbreak|override|disable\s+guardrail", re.IGNORECASE),
]

OUTPUT_BLOCKLIST = [
    re.compile(r"api[_-]?key", re.IGNORECASE),
    re.compile(r"password\s*[:=]", re.IGNORECASE),
]


def pre_generation_guardrail(text: str) -> tuple[bool, str]:
    for pattern in BLOCKLIST_PATTERNS:
        if pattern.search(text):
            return False, "Your prompt contains blocked instruction patterns."

    if len(text) > 12000:
        return False, "Input is too large."

    return True, text.strip()


def detect_pii(text: str) -> bool:
    return any(pattern.search(text) for pattern in PII_PATTERNS)


def post_generation_guardrail(answer: str, citations: list[dict]) -> str:
    if not citations:
        return "I could not find grounded sources for this answer."

    for pattern in OUTPUT_BLOCKLIST:
        if pattern.search(answer):
            return "I cannot share sensitive credential-like data."

    if detect_pii(answer):
        answer = "[REDACTED_PII] " + answer

    return answer
