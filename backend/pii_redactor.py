import re

# Comprehensive PII scrubbing regex patterns
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
API_KEY_REGEX = re.compile(r'(?:AIzaSy|sk-|bearer\s+)[A-Za-z0-9_\-]{20,}', re.IGNORECASE)
PHONE_REGEX = re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
SSN_REGEX = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
IP_REGEX = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')

def redact_pii(text: str) -> str:
    """
    Scrubs Personally Identifiable Information (PII) and secret credentials from strings
    before logging, emitting trace events, or transmitting messages.
    """
    if not isinstance(text, str):
        return text

    scrubbed = text
    scrubbed = API_KEY_REGEX.sub("[API_KEY_REDACTED]", scrubbed)
    scrubbed = EMAIL_REGEX.sub("[EMAIL_REDACTED]", scrubbed)
    scrubbed = PHONE_REGEX.sub("[PHONE_REDACTED]", scrubbed)
    scrubbed = SSN_REGEX.sub("[SSN_REDACTED]", scrubbed)
    scrubbed = IP_REGEX.sub("[IP_REDACTED]", scrubbed)

    return scrubbed
