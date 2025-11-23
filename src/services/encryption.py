"""Encryption utilities for anonymous voting.

Provides AES-256-GCM symmetric encryption for user ID anonymization during active voting rounds.
"""

import logging
import os
import base64
from typing import Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

logger = logging.getLogger(__name__)


class VotingEncryptionService:
    """Service for encrypting and decrypting user IDs in voting rounds.

    Uses AES-256-GCM (Galois/Counter Mode) for authenticated encryption.
    """

    def __init__(self, encryption_key: bytes):
        """Initialize encryption service.

        Args:
            encryption_key: 32-byte encryption key for AES-256
        """
        if len(encryption_key) != 32:
            raise ValueError("Encryption key must be exactly 32 bytes for AES-256")

        self.aesgcm = AESGCM(encryption_key)

    @classmethod
    def from_passphrase(cls, passphrase: str, salt: bytes) -> "VotingEncryptionService":
        """Create encryption service from passphrase using key derivation.

        Args:
            passphrase: Human-readable passphrase
            salt: Salt for key derivation (should be stored securely)

        Returns:
            VotingEncryptionService instance
        """
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,  # OWASP recommendation for 2024
        )
        key = kdf.derive(passphrase.encode("utf-8"))
        return cls(key)

    def encrypt_user_id(self, user_id: str) -> str:
        """Encrypt user ID for anonymous voting.

        Args:
            user_id: Plaintext user ID

        Returns:
            Base64-encoded encrypted user ID (includes nonce)
        """
        # Generate random nonce (96 bits for GCM)
        nonce = os.urandom(12)

        # Encrypt user ID
        plaintext = user_id.encode("utf-8")
        ciphertext = self.aesgcm.encrypt(nonce, plaintext, None)

        # Combine nonce + ciphertext and encode
        encrypted_data = nonce + ciphertext
        encrypted_b64 = base64.urlsafe_b64encode(encrypted_data).decode("utf-8")

        logger.debug(f"Encrypted user ID (length: {len(user_id)} → {len(encrypted_b64)})")

        return encrypted_b64

    def decrypt_user_id(self, encrypted_user_id: str) -> str:
        """Decrypt user ID after voting round closes.

        Args:
            encrypted_user_id: Base64-encoded encrypted user ID

        Returns:
            Plaintext user ID

        Raises:
            ValueError: If decryption fails (tampering or wrong key)
        """
        try:
            # Decode from base64
            encrypted_data = base64.urlsafe_b64decode(encrypted_user_id.encode("utf-8"))

            # Extract nonce (first 12 bytes) and ciphertext
            nonce = encrypted_data[:12]
            ciphertext = encrypted_data[12:]

            # Decrypt
            plaintext = self.aesgcm.decrypt(nonce, ciphertext, None)
            user_id = plaintext.decode("utf-8")

            logger.debug(f"Decrypted user ID (length: {len(encrypted_user_id)} → {len(user_id)})")

            return user_id

        except Exception as e:
            logger.error(f"Decryption failed: {e}", exc_info=True)
            raise ValueError(f"Failed to decrypt user ID: {e}")

    def encrypt_multiple(self, user_ids: list[str]) -> dict[str, str]:
        """Encrypt multiple user IDs in batch.

        Args:
            user_ids: List of plaintext user IDs

        Returns:
            Dict mapping plaintext → encrypted user IDs
        """
        return {uid: self.encrypt_user_id(uid) for uid in user_ids}

    def decrypt_multiple(self, encrypted_user_ids: list[str]) -> dict[str, str]:
        """Decrypt multiple user IDs in batch.

        Args:
            encrypted_user_ids: List of encrypted user IDs

        Returns:
            Dict mapping encrypted → plaintext user IDs
        """
        decrypted = {}
        for enc_uid in encrypted_user_ids:
            try:
                decrypted[enc_uid] = self.decrypt_user_id(enc_uid)
            except ValueError as e:
                logger.warning(f"Skipping failed decryption for {enc_uid[:20]}...: {e}")
                continue

        return decrypted


# ============================================================================
# KEY MANAGEMENT UTILITIES
# ============================================================================


def generate_encryption_key() -> bytes:
    """Generate a random 32-byte encryption key for AES-256.

    Returns:
        32-byte random key

    Note:
        In production, store this key securely (e.g., AWS KMS, HashiCorp Vault)
    """
    return os.urandom(32)


def generate_salt() -> bytes:
    """Generate a random salt for key derivation.

    Returns:
        16-byte random salt

    Note:
        Store this salt alongside the encrypted data
    """
    return os.urandom(16)


def key_to_base64(key: bytes) -> str:
    """Encode encryption key to base64 for storage.

    Args:
        key: Raw encryption key

    Returns:
        Base64-encoded key
    """
    return base64.b64encode(key).decode("utf-8")


def key_from_base64(key_b64: str) -> bytes:
    """Decode encryption key from base64.

    Args:
        key_b64: Base64-encoded key

    Returns:
        Raw encryption key
    """
    return base64.b64decode(key_b64.encode("utf-8"))


# ============================================================================
# SINGLETON INSTANCE (for application-wide use)
# ============================================================================

_encryption_service: VotingEncryptionService | None = None


def get_encryption_service(
    encryption_key: bytes | None = None,
    passphrase: str | None = None,
    salt: bytes | None = None,
) -> VotingEncryptionService:
    """Get or create encryption service singleton.

    Args:
        encryption_key: Optional 32-byte encryption key
        passphrase: Optional passphrase (requires salt)
        salt: Optional salt for passphrase-based key derivation

    Returns:
        VotingEncryptionService instance

    Note:
        First call must provide either encryption_key or (passphrase + salt)
    """
    global _encryption_service

    if _encryption_service is None:
        if encryption_key:
            _encryption_service = VotingEncryptionService(encryption_key)
        elif passphrase and salt:
            _encryption_service = VotingEncryptionService.from_passphrase(passphrase, salt)
        else:
            # Development fallback: generate random key (not for production!)
            logger.warning(
                "No encryption key or passphrase provided. "
                "Generating random key (NOT SUITABLE FOR PRODUCTION)"
            )
            random_key = generate_encryption_key()
            _encryption_service = VotingEncryptionService(random_key)

    return _encryption_service
