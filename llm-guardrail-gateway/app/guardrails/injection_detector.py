import re

class InjectionDetector:
    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
        r"system\s*override",
        r"disregard\s+(the\s+)?system\s+prompt",
        r"you\s+are\s+now\s+in\s+DAN\s+mode",
        r"output\s+the\s+initial\s+system\s+message",
        r"developer\s+mode\s+enabled",
        r"<\|start_header_id\|>system"
    ]

    @classmethod
    def is_adversarial(cls, text: str) -> tuple[bool, str]:
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return True, f"Triggered adversarial pattern: '{pattern}'"
        return False, ""