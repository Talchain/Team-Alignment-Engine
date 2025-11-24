"""Unit tests for encryption service (SECURITY-CRITICAL).

These tests ensure the encryption service properly protects user IDs during anonymous voting.
"""

import pytest
import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from src.services.encryption import (
    VotingEncryptionService,
    generate_encryption_key,
    generate_salt,
    key_to_base64,
    key_from_base64,
)


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================


def test_init_with_valid_key():
    """Test initializing encryption service with valid 32-byte key."""
    key = os.urandom(32)
    service = VotingEncryptionService(key)
    assert service.aesgcm is not None


def test_init_with_invalid_key_length():
    """Test initializing with wrong key length raises error."""
    # Too short
    with pytest.raises(ValueError, match="must be exactly 32 bytes"):
        VotingEncryptionService(os.urandom(16))

    # Too long
    with pytest.raises(ValueError, match="must be exactly 32 bytes"):
        VotingEncryptionService(os.urandom(64))


def test_from_passphrase():
    """Test creating service from passphrase."""
    passphrase = "my-secure-passphrase-for-voting"
    salt = os.urandom(16)

    service = VotingEncryptionService.from_passphrase(passphrase, salt)
    assert service.aesgcm is not None


def test_from_passphrase_deterministic():
    """Test same passphrase + salt produces same key (deterministic)."""
    passphrase = "test-passphrase"
    salt = os.urandom(16)

    service1 = VotingEncryptionService.from_passphrase(passphrase, salt)
    service2 = VotingEncryptionService.from_passphrase(passphrase, salt)

    # Same passphrase + salt should encrypt to same value
    user_id = "user-123"
    enc1 = service1.encrypt_user_id(user_id)
    enc2 = service2.encrypt_user_id(user_id)

    # Decryption should work with either service
    assert service1.decrypt_user_id(enc2) == user_id
    assert service2.decrypt_user_id(enc1) == user_id


# =============================================================================
# ENCRYPTION/DECRYPTION TESTS
# =============================================================================


def test_encrypt_decrypt_roundtrip():
    """Test encrypting and decrypting user ID returns original value."""
    key = generate_encryption_key()
    service = VotingEncryptionService(key)

    user_id = "user-abc-123"
    encrypted = service.encrypt_user_id(user_id)
    decrypted = service.decrypt_user_id(encrypted)

    assert decrypted == user_id


def test_encrypted_format():
    """Test encrypted value is properly base64-encoded."""
    key = generate_encryption_key()
    service = VotingEncryptionService(key)

    user_id = "user-123"
    encrypted = service.encrypt_user_id(user_id)

    # Should be valid URL-safe base64
    assert isinstance(encrypted, str)
    assert len(encrypted) > 0

    # Should be decodable as base64
    try:
        decoded = base64.urlsafe_b64decode(encrypted)
        assert len(decoded) > 12  # At least nonce (12 bytes) + ciphertext
    except Exception as e:
        pytest.fail(f"Encrypted value is not valid base64: {e}")


def test_encryption_is_non_deterministic():
    """Test same user_id encrypts to different ciphertext each time (due to random nonce)."""
    key = generate_encryption_key()
    service = VotingEncryptionService(key)

    user_id = "user-123"
    enc1 = service.encrypt_user_id(user_id)
    enc2 = service.encrypt_user_id(user_id)

    # Different nonces should produce different ciphertexts
    assert enc1 != enc2

    # But both should decrypt to same value
    assert service.decrypt_user_id(enc1) == user_id
    assert service.decrypt_user_id(enc2) == user_id


def test_decrypt_with_wrong_key_fails():
    """Test decrypting with wrong key raises error."""
    key1 = generate_encryption_key()
    key2 = generate_encryption_key()

    service1 = VotingEncryptionService(key1)
    service2 = VotingEncryptionService(key2)

    user_id = "user-123"
    encrypted = service1.encrypt_user_id(user_id)

    # Decryption with wrong key should fail
    with pytest.raises(ValueError, match="Failed to decrypt"):
        service2.decrypt_user_id(encrypted)


def test_decrypt_tampered_ciphertext_fails():
    """Test decrypting tampered ciphertext raises error (authenticated encryption)."""
    key = generate_encryption_key()
    service = VotingEncryptionService(key)

    user_id = "user-123"
    encrypted = service.encrypt_user_id(user_id)

    # Tamper with the ciphertext
    tampered = encrypted[:-5] + "XXXXX"

    # Decryption should fail due to authentication tag mismatch
    with pytest.raises(ValueError, match="Failed to decrypt"):
        service.decrypt_user_id(tampered)


def test_decrypt_invalid_base64_fails():
    """Test decrypting invalid base64 raises error."""
    key = generate_encryption_key()
    service = VotingEncryptionService(key)

    invalid_b64 = "not-valid-base64!!!"

    with pytest.raises(ValueError, match="Failed to decrypt"):
        service.decrypt_user_id(invalid_b64)


# =============================================================================
# BATCH OPERATIONS TESTS
# =============================================================================


def test_encrypt_multiple():
    """Test encrypting multiple user IDs."""
    key = generate_encryption_key()
    service = VotingEncryptionService(key)

    user_ids = ["user-1", "user-2", "user-3"]
    encrypted_map = service.encrypt_multiple(user_ids)

    assert len(encrypted_map) == 3
    for user_id in user_ids:
        assert user_id in encrypted_map
        assert service.decrypt_user_id(encrypted_map[user_id]) == user_id


def test_decrypt_multiple():
    """Test decrypting multiple user IDs."""
    key = generate_encryption_key()
    service = VotingEncryptionService(key)

    user_ids = ["user-1", "user-2", "user-3"]
    encrypted_map = service.encrypt_multiple(user_ids)
    encrypted_ids = list(encrypted_map.values())

    decrypted_map = service.decrypt_multiple(encrypted_ids)

    assert len(decrypted_map) == 3
    for enc_id, user_id in decrypted_map.items():
        assert user_id in user_ids


def test_decrypt_multiple_with_failures():
    """Test batch decryption handles failures gracefully."""
    key = generate_encryption_key()
    service = VotingEncryptionService(key)

    # Mix of valid and invalid encrypted IDs
    valid_enc = service.encrypt_user_id("user-1")
    encrypted_ids = [
        valid_enc,
        "invalid-base64!!!",
        service.encrypt_user_id("user-2"),
    ]

    decrypted_map = service.decrypt_multiple(encrypted_ids)

    # Should have 2 successful decryptions, skip 1 invalid
    assert len(decrypted_map) == 2
    assert decrypted_map[valid_enc] == "user-1"


# =============================================================================
# EDGE CASES
# =============================================================================


def test_encrypt_empty_string():
    """Test encrypting empty user ID."""
    key = generate_encryption_key()
    service = VotingEncryptionService(key)

    user_id = ""
    encrypted = service.encrypt_user_id(user_id)
    decrypted = service.decrypt_user_id(encrypted)

    assert decrypted == ""


def test_encrypt_special_characters():
    """Test encrypting user IDs with special characters."""
    key = generate_encryption_key()
    service = VotingEncryptionService(key)

    user_ids = [
        "user@example.com",
        "user-with-dashes-123",
        "user_with_underscores",
        "用户-unicode",
    ]

    for user_id in user_ids:
        encrypted = service.encrypt_user_id(user_id)
        decrypted = service.decrypt_user_id(encrypted)
        assert decrypted == user_id


def test_encrypt_long_user_id():
    """Test encrypting very long user ID."""
    key = generate_encryption_key()
    service = VotingEncryptionService(key)

    user_id = "a" * 1000  # Very long ID
    encrypted = service.encrypt_user_id(user_id)
    decrypted = service.decrypt_user_id(encrypted)

    assert decrypted == user_id


# =============================================================================
# KEY MANAGEMENT UTILITIES TESTS
# =============================================================================


def test_generate_encryption_key():
    """Test key generation produces 32-byte keys."""
    key = generate_encryption_key()
    assert len(key) == 32
    assert isinstance(key, bytes)


def test_generate_salt():
    """Test salt generation produces 16-byte salts."""
    salt = generate_salt()
    assert len(salt) == 16
    assert isinstance(salt, bytes)


def test_key_to_base64_roundtrip():
    """Test key base64 encoding/decoding."""
    key = generate_encryption_key()
    encoded = key_to_base64(key)
    decoded = key_from_base64(encoded)

    assert decoded == key


def test_key_base64_format():
    """Test key base64 encoding produces valid string."""
    key = generate_encryption_key()
    encoded = key_to_base64(key)

    assert isinstance(encoded, str)
    assert len(encoded) > 0

    # Should be valid base64
    try:
        base64.b64decode(encoded)
    except Exception as e:
        pytest.fail(f"Encoded key is not valid base64: {e}")


# =============================================================================
# SECURITY PROPERTIES TESTS
# =============================================================================


def test_nonce_is_random():
    """Test that nonce is randomized for each encryption (prevents replay attacks)."""
    key = generate_encryption_key()
    service = VotingEncryptionService(key)

    user_id = "user-123"

    # Encrypt multiple times
    encrypted_values = [service.encrypt_user_id(user_id) for _ in range(10)]

    # All encrypted values should be different (different nonces)
    assert len(set(encrypted_values)) == 10


def test_authentication_prevents_tampering():
    """Test GCM authentication prevents ciphertext tampering."""
    key = generate_encryption_key()
    service = VotingEncryptionService(key)

    user_id = "user-123"
    encrypted = service.encrypt_user_id(user_id)

    # Decode to get raw data
    encrypted_data = base64.urlsafe_b64decode(encrypted)

    # Tamper with a byte in the ciphertext (not nonce)
    tampered_data = bytearray(encrypted_data)
    tampered_data[15] ^= 0xFF  # Flip bits in ciphertext
    tampered_b64 = base64.urlsafe_b64encode(bytes(tampered_data)).decode()

    # Decryption should fail due to authentication tag mismatch
    with pytest.raises(ValueError):
        service.decrypt_user_id(tampered_b64)


def test_different_salts_produce_different_keys():
    """Test different salts produce different encryption keys."""
    passphrase = "same-passphrase"
    salt1 = generate_salt()
    salt2 = generate_salt()

    service1 = VotingEncryptionService.from_passphrase(passphrase, salt1)
    service2 = VotingEncryptionService.from_passphrase(passphrase, salt2)

    user_id = "user-123"
    enc1 = service1.encrypt_user_id(user_id)

    # Decryption with different salt should fail
    with pytest.raises(ValueError):
        service2.decrypt_user_id(enc1)
