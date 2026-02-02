"""Authentication service for code and OTP generation."""

import secrets
import string


def generate_code() -> str:
    """Generate a 6-character alphanumeric lowercase code."""
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))


def generate_otp() -> str:
    """Generate a 4-digit OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(4))


def is_valid_code(code: str) -> bool:
    """Validate code format: 6 alphanumeric lowercase characters."""
    if len(code) != 6:
        return False
    return code.isalnum() and code.islower()
