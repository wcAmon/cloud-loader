"""Authentication service for code and API key generation."""

import secrets
import string


def generate_code() -> str:
    """Generate a 6-character alphanumeric lowercase code."""
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))


def is_valid_code(code: str) -> bool:
    """Validate code format: 6 alphanumeric lowercase characters."""
    if len(code) != 6:
        return False
    return code.isalnum() and code.islower()


def generate_api_key() -> str:
    """Generate an API key with 'll_' prefix (loader.land)."""
    # 32 chars of random alphanumeric
    alphabet = string.ascii_letters + string.digits
    random_part = "".join(secrets.choice(alphabet) for _ in range(32))
    return f"ll_{random_part}"


def generate_user_id() -> str:
    """Generate a user ID with 'usr_' prefix."""
    alphabet = string.ascii_lowercase + string.digits
    random_part = "".join(secrets.choice(alphabet) for _ in range(12))
    return f"usr_{random_part}"


def is_valid_api_key(api_key: str) -> bool:
    """Validate API key format."""
    if not api_key or not api_key.startswith("ll_"):
        return False
    return len(api_key) == 35  # ll_ + 32 chars
