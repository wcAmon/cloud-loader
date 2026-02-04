"""Tests for auth service."""

from cloud_loader.services.auth import generate_code, is_valid_code


def test_generate_code_length():
    """Generated code should be 6 characters."""
    code = generate_code()
    assert len(code) == 6


def test_generate_code_alphanumeric():
    """Generated code should be alphanumeric lowercase."""
    code = generate_code()
    assert code.isalnum()
    assert code.islower()


def test_generate_code_unique():
    """Generated codes should be unique."""
    codes = {generate_code() for _ in range(100)}
    assert len(codes) == 100


def test_is_valid_code_correct():
    """Valid code should pass validation."""
    assert is_valid_code("abc123") is True
    assert is_valid_code("xyz789") is True


def test_is_valid_code_wrong_length():
    """Code with wrong length should fail."""
    assert is_valid_code("abc") is False
    assert is_valid_code("abc12345") is False


def test_is_valid_code_invalid_chars():
    """Code with invalid characters should fail."""
    assert is_valid_code("ABC123") is False
    assert is_valid_code("abc-12") is False
