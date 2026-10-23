import re

class PIISanitizer:
    EMAIL_PATTERN = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    PHONE_PATTERN = r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    EMPLOYEE_ID_PATTERN = r'\b(EMP|TCS|ID)-?\d{4,7}\b'

    @classmethod
    def sanitize(cls, text: str) -> tuple[str, bool]:
        sanitized = text
        redacted = False

        if re.search(cls.EMAIL_PATTERN, sanitized):
            sanitized = re.sub(cls.EMAIL_PATTERN, "[REDACTED_EMAIL]", sanitized)
            redacted = True

        if re.search(cls.PHONE_PATTERN, sanitized):
            sanitized = re.sub(cls.PHONE_PATTERN, "[REDACTED_PHONE]", sanitized)
            redacted = True

        if re.search(cls.EMPLOYEE_ID_PATTERN, sanitized, flags=re.IGNORECASE):
            sanitized = re.sub(cls.EMPLOYEE_ID_PATTERN, "[REDACTED_EMP_ID]", sanitized)
            redacted = True

        return sanitized, redacted