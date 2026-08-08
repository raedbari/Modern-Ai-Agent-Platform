"""Unit tests for tenant JWT refresh token utilities.

Tests for task 3.1: Create refresh token utilities.
Validates Requirements 1.10, 1.11, 3.5.
"""

import pytest

from backend.app.auth.tenant_jwt import generate_refresh_token, hash_token


class TestGenerateRefreshToken:
    """Tests for generate_refresh_token function."""

    def test_token_format_has_correct_prefix(self):
        """Token should start with 'maap_usr_' prefix."""
        token = generate_refresh_token()
        assert token.startswith("maap_usr_"), f"Token should start with 'maap_usr_' but got: {token[:15]}"

    def test_token_has_sufficient_length(self):
        """Token should have sufficient length for security (prefix + random part)."""
        token = generate_refresh_token()
        # maap_usr_ (9 chars) + base64url(32 bytes) ≈ 43 chars = ~52 total chars
        assert len(token) > 40, f"Token should be > 40 chars, got {len(token)}"

    def test_tokens_are_unique(self):
        """Each generated token should be different."""
        token1 = generate_refresh_token()
        token2 = generate_refresh_token()
        token3 = generate_refresh_token()
        
        assert token1 != token2
        assert token2 != token3
        assert token1 != token3

    def test_token_is_url_safe(self):
        """Token should only contain URL-safe characters."""
        token = generate_refresh_token()
        # URL-safe base64 uses: A-Z, a-z, 0-9, -, _
        # Plus our prefix uses underscore
        allowed_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
        for char in token:
            assert char in allowed_chars, f"Token contains non-URL-safe character: {char}"


class TestHashToken:
    """Tests for hash_token function."""

    def test_hash_length_is_64_characters(self):
        """SHA-256 hex digest should be exactly 64 characters."""
        token = "test_token_123"
        token_hash = hash_token(token)
        assert len(token_hash) == 64, f"Hash should be 64 chars, got {len(token_hash)}"

    def test_hash_is_hexadecimal(self):
        """Hash should only contain hexadecimal characters (0-9, a-f)."""
        token = "test_token_456"
        token_hash = hash_token(token)
        
        hex_chars = set("0123456789abcdef")
        for char in token_hash:
            assert char in hex_chars, f"Hash contains non-hex character: {char}"

    def test_same_input_produces_same_hash(self):
        """Hashing the same token multiple times should produce identical hashes."""
        token = "consistent_token"
        hash1 = hash_token(token)
        hash2 = hash_token(token)
        hash3 = hash_token(token)
        
        assert hash1 == hash2 == hash3

    def test_different_inputs_produce_different_hashes(self):
        """Different tokens should produce different hashes."""
        token1 = "token_one"
        token2 = "token_two"
        token3 = "token_three"
        
        hash1 = hash_token(token1)
        hash2 = hash_token(token2)
        hash3 = hash_token(token3)
        
        assert hash1 != hash2
        assert hash2 != hash3
        assert hash1 != hash3

    def test_hash_handles_empty_string(self):
        """Hash function should handle empty string input."""
        token_hash = hash_token("")
        assert len(token_hash) == 64
        # SHA-256 of empty string is known value
        assert token_hash == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def test_hash_handles_special_characters(self):
        """Hash function should handle special characters."""
        token = "token_with_special!@#$%^&*()_+-=[]{}|;':,.<>?/"
        token_hash = hash_token(token)
        assert len(token_hash) == 64

    def test_hash_handles_unicode(self):
        """Hash function should handle Unicode characters."""
        token = "token_with_unicode_😀🎉"
        token_hash = hash_token(token)
        assert len(token_hash) == 64


class TestIntegration:
    """Integration tests combining both functions."""

    def test_generated_token_can_be_hashed(self):
        """A generated refresh token should be hashable."""
        token = generate_refresh_token()
        token_hash = hash_token(token)
        
        assert len(token_hash) == 64
        assert all(c in "0123456789abcdef" for c in token_hash)

    def test_multiple_tokens_produce_unique_hashes(self):
        """Multiple generated tokens should produce unique hashes."""
        tokens = [generate_refresh_token() for _ in range(10)]
        hashes = [hash_token(token) for token in tokens]
        
        # All tokens should be unique
        assert len(set(tokens)) == 10
        
        # All hashes should be unique
        assert len(set(hashes)) == 10

    def test_hash_comparison_workflow(self):
        """Simulate the workflow of storing and comparing token hashes."""
        # Simulate: User logs in, we generate a token
        refresh_token = generate_refresh_token()
        
        # Simulate: We hash and store it in the database
        stored_hash = hash_token(refresh_token)
        
        # Simulate: User presents the token later
        presented_token = refresh_token
        
        # Simulate: We hash the presented token and compare
        presented_hash = hash_token(presented_token)
        
        # The hashes should match
        assert stored_hash == presented_hash
        
        # Simulate: Wrong token presented
        wrong_token = generate_refresh_token()
        wrong_hash = hash_token(wrong_token)
        
        # The hashes should NOT match
        assert stored_hash != wrong_hash
