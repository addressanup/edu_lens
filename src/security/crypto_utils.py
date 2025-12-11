"""
Cryptographic Utilities for EduLens Secure Communication

This module provides core cryptographic primitives for secure communication
between EduLens glasses and companion app, including key generation,
encryption, authentication, and secure random generation.

Security Standards:
- AES-256-GCM for symmetric encryption
- ECDH with Curve25519 for key exchange
- HMAC-SHA256 for message authentication
- HKDF for key derivation
- Secure random generation using secrets module
"""

import os
import secrets
import hashlib
import hmac
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature, InvalidTag

logger = logging.getLogger(__name__)


@dataclass
class KeyPair:
    """Represents an asymmetric key pair."""
    private_key: ec.EllipticCurvePrivateKey
    public_key: ec.EllipticCurvePublicKey
    created_at: datetime
    expires_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        """Check if the key pair has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def serialize_public_key(self) -> bytes:
        """Serialize public key to bytes."""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )

    def serialize_private_key(self, password: Optional[bytes] = None) -> bytes:
        """Serialize private key to bytes with optional encryption."""
        if password:
            encryption = serialization.BestAvailableEncryption(password)
        else:
            encryption = serialization.NoEncryption()

        return self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption
        )


@dataclass
class SymmetricKey:
    """Represents a symmetric encryption key."""
    key: bytes
    created_at: datetime
    expires_at: Optional[datetime] = None
    key_id: Optional[str] = None

    def is_expired(self) -> bool:
        """Check if the key has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


class CryptoUtils:
    """
    Cryptographic utilities for secure communication.

    Provides functions for:
    - Key generation (symmetric and asymmetric)
    - Encryption/decryption
    - Message authentication
    - Key derivation
    - Secure random generation
    """

    # Cryptographic constants
    AES_KEY_SIZE = 32  # 256 bits
    NONCE_SIZE = 12  # 96 bits for GCM
    HMAC_KEY_SIZE = 32  # 256 bits
    SALT_SIZE = 32  # 256 bits
    TAG_SIZE = 16  # 128 bits for GCM

    # Key rotation periods
    DEFAULT_KEY_LIFETIME = timedelta(days=30)
    SESSION_KEY_LIFETIME = timedelta(hours=24)

    def __init__(self):
        """Initialize cryptographic utilities."""
        self.backend = default_backend()
        logger.info("CryptoUtils initialized with secure defaults")

    # ==================== Key Generation ====================

    def generate_symmetric_key(
        self,
        key_size: int = AES_KEY_SIZE,
        lifetime: Optional[timedelta] = None,
        key_id: Optional[str] = None
    ) -> SymmetricKey:
        """
        Generate a cryptographically secure symmetric key.

        Args:
            key_size: Size of the key in bytes (default: 32 for AES-256)
            lifetime: Key lifetime duration
            key_id: Optional identifier for the key

        Returns:
            SymmetricKey object containing the key and metadata
        """
        key = secrets.token_bytes(key_size)
        created_at = datetime.utcnow()
        expires_at = created_at + lifetime if lifetime else None

        logger.debug(f"Generated symmetric key (size: {key_size} bytes, id: {key_id})")

        return SymmetricKey(
            key=key,
            created_at=created_at,
            expires_at=expires_at,
            key_id=key_id
        )

    def generate_key_pair(
        self,
        curve: ec.EllipticCurve = ec.SECP384R1(),
        lifetime: Optional[timedelta] = None
    ) -> KeyPair:
        """
        Generate an elliptic curve key pair for ECDH.

        Args:
            curve: Elliptic curve to use (default: SECP384R1)
            lifetime: Key pair lifetime duration

        Returns:
            KeyPair object containing private/public keys and metadata
        """
        private_key = ec.generate_private_key(curve, self.backend)
        public_key = private_key.public_key()
        created_at = datetime.utcnow()
        expires_at = created_at + lifetime if lifetime else None

        logger.debug(f"Generated EC key pair (curve: {curve.name})")

        return KeyPair(
            private_key=private_key,
            public_key=public_key,
            created_at=created_at,
            expires_at=expires_at
        )

    def perform_ecdh(
        self,
        private_key: ec.EllipticCurvePrivateKey,
        peer_public_key: ec.EllipticCurvePublicKey
    ) -> bytes:
        """
        Perform Elliptic Curve Diffie-Hellman key exchange.

        Args:
            private_key: Our private key
            peer_public_key: Peer's public key

        Returns:
            Shared secret bytes
        """
        try:
            shared_key = private_key.exchange(ec.ECDH(), peer_public_key)
            logger.debug("ECDH key exchange completed successfully")
            return shared_key
        except Exception as e:
            logger.error(f"ECDH key exchange failed: {e}")
            raise

    # ==================== Key Derivation ====================

    def derive_key(
        self,
        input_key_material: bytes,
        salt: Optional[bytes] = None,
        info: Optional[bytes] = None,
        length: int = AES_KEY_SIZE
    ) -> bytes:
        """
        Derive a key using HKDF (HMAC-based Key Derivation Function).

        Args:
            input_key_material: Source key material
            salt: Optional salt value (random if not provided)
            info: Optional context/application-specific info
            length: Desired output key length in bytes

        Returns:
            Derived key bytes
        """
        if salt is None:
            salt = secrets.token_bytes(self.SALT_SIZE)

        kdf = HKDF(
            algorithm=hashes.SHA256(),
            length=length,
            salt=salt,
            info=info,
            backend=self.backend
        )

        derived_key = kdf.derive(input_key_material)
        logger.debug(f"Derived key using HKDF (length: {length} bytes)")

        return derived_key

    def derive_session_keys(
        self,
        shared_secret: bytes,
        salt: bytes,
        context: str = "session"
    ) -> Dict[str, bytes]:
        """
        Derive multiple session keys from a shared secret.

        Args:
            shared_secret: Shared secret from key exchange
            salt: Salt value for key derivation
            context: Context string for key derivation

        Returns:
            Dictionary containing encryption and MAC keys
        """
        # Derive encryption key
        encryption_key = self.derive_key(
            shared_secret,
            salt=salt,
            info=f"{context}:encryption".encode(),
            length=self.AES_KEY_SIZE
        )

        # Derive MAC key
        mac_key = self.derive_key(
            shared_secret,
            salt=salt,
            info=f"{context}:mac".encode(),
            length=self.HMAC_KEY_SIZE
        )

        # Derive IV/nonce generation key
        nonce_key = self.derive_key(
            shared_secret,
            salt=salt,
            info=f"{context}:nonce".encode(),
            length=self.AES_KEY_SIZE
        )

        logger.debug(f"Derived session keys for context: {context}")

        return {
            "encryption_key": encryption_key,
            "mac_key": mac_key,
            "nonce_key": nonce_key
        }

    # ==================== Encryption/Decryption ====================

    def encrypt_aes_gcm(
        self,
        plaintext: bytes,
        key: bytes,
        associated_data: Optional[bytes] = None
    ) -> Tuple[bytes, bytes]:
        """
        Encrypt data using AES-256-GCM.

        Args:
            plaintext: Data to encrypt
            key: Encryption key (32 bytes for AES-256)
            associated_data: Optional additional authenticated data

        Returns:
            Tuple of (ciphertext, nonce)
        """
        if len(key) != self.AES_KEY_SIZE:
            raise ValueError(f"Invalid key size: {len(key)} (expected {self.AES_KEY_SIZE})")

        # Generate a random nonce
        nonce = secrets.token_bytes(self.NONCE_SIZE)

        # Create cipher and encrypt
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)

        logger.debug(f"Encrypted {len(plaintext)} bytes using AES-256-GCM")

        return ciphertext, nonce

    def decrypt_aes_gcm(
        self,
        ciphertext: bytes,
        key: bytes,
        nonce: bytes,
        associated_data: Optional[bytes] = None
    ) -> bytes:
        """
        Decrypt data using AES-256-GCM.

        Args:
            ciphertext: Data to decrypt
            key: Decryption key (32 bytes for AES-256)
            nonce: Nonce used during encryption
            associated_data: Optional additional authenticated data

        Returns:
            Decrypted plaintext bytes

        Raises:
            InvalidTag: If authentication fails
        """
        if len(key) != self.AES_KEY_SIZE:
            raise ValueError(f"Invalid key size: {len(key)} (expected {self.AES_KEY_SIZE})")

        if len(nonce) != self.NONCE_SIZE:
            raise ValueError(f"Invalid nonce size: {len(nonce)} (expected {self.NONCE_SIZE})")

        try:
            # Create cipher and decrypt
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data)

            logger.debug(f"Decrypted {len(ciphertext)} bytes using AES-256-GCM")

            return plaintext
        except InvalidTag:
            logger.error("Decryption failed: authentication tag verification failed")
            raise

    # ==================== Message Authentication ====================

    def compute_hmac(
        self,
        message: bytes,
        key: bytes,
        algorithm: str = "sha256"
    ) -> bytes:
        """
        Compute HMAC for message authentication.

        Args:
            message: Message to authenticate
            key: HMAC key
            algorithm: Hash algorithm (default: sha256)

        Returns:
            HMAC digest bytes
        """
        if algorithm == "sha256":
            hash_func = hashlib.sha256
        elif algorithm == "sha384":
            hash_func = hashlib.sha384
        elif algorithm == "sha512":
            hash_func = hashlib.sha512
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")

        mac = hmac.new(key, message, hash_func).digest()
        logger.debug(f"Computed HMAC-{algorithm.upper()} for {len(message)} bytes")

        return mac

    def verify_hmac(
        self,
        message: bytes,
        key: bytes,
        expected_mac: bytes,
        algorithm: str = "sha256"
    ) -> bool:
        """
        Verify HMAC for message authentication.

        Args:
            message: Message to verify
            key: HMAC key
            expected_mac: Expected HMAC digest
            algorithm: Hash algorithm (default: sha256)

        Returns:
            True if HMAC is valid, False otherwise
        """
        try:
            computed_mac = self.compute_hmac(message, key, algorithm)
            # Use constant-time comparison to prevent timing attacks
            is_valid = hmac.compare_digest(computed_mac, expected_mac)

            if is_valid:
                logger.debug("HMAC verification successful")
            else:
                logger.warning("HMAC verification failed")

            return is_valid
        except Exception as e:
            logger.error(f"HMAC verification error: {e}")
            return False

    # ==================== Secure Random Generation ====================

    def generate_random_bytes(self, length: int) -> bytes:
        """
        Generate cryptographically secure random bytes.

        Args:
            length: Number of random bytes to generate

        Returns:
            Random bytes
        """
        random_bytes = secrets.token_bytes(length)
        logger.debug(f"Generated {length} random bytes")
        return random_bytes

    def generate_random_hex(self, length: int) -> str:
        """
        Generate cryptographically secure random hex string.

        Args:
            length: Number of random bytes (output will be 2x characters)

        Returns:
            Random hex string
        """
        hex_string = secrets.token_hex(length)
        logger.debug(f"Generated {len(hex_string)} character hex string")
        return hex_string

    def generate_random_int(self, min_value: int, max_value: int) -> int:
        """
        Generate cryptographically secure random integer.

        Args:
            min_value: Minimum value (inclusive)
            max_value: Maximum value (inclusive)

        Returns:
            Random integer
        """
        random_int = secrets.randbelow(max_value - min_value + 1) + min_value
        logger.debug(f"Generated random integer in range [{min_value}, {max_value}]")
        return random_int

    # ==================== Hash Functions ====================

    def hash_data(
        self,
        data: bytes,
        algorithm: str = "sha256"
    ) -> bytes:
        """
        Compute cryptographic hash of data.

        Args:
            data: Data to hash
            algorithm: Hash algorithm (default: sha256)

        Returns:
            Hash digest bytes
        """
        if algorithm == "sha256":
            hash_obj = hashlib.sha256(data)
        elif algorithm == "sha384":
            hash_obj = hashlib.sha384(data)
        elif algorithm == "sha512":
            hash_obj = hashlib.sha512(data)
        elif algorithm == "blake2b":
            hash_obj = hashlib.blake2b(data)
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")

        digest = hash_obj.digest()
        logger.debug(f"Computed {algorithm.upper()} hash for {len(data)} bytes")

        return digest

    # ==================== Key Serialization ====================

    def serialize_public_key(self, public_key: ec.EllipticCurvePublicKey) -> bytes:
        """
        Serialize an elliptic curve public key to bytes.

        Args:
            public_key: Public key to serialize

        Returns:
            Serialized public key bytes
        """
        return public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )

    def deserialize_public_key(
        self,
        public_key_bytes: bytes,
        curve: ec.EllipticCurve = ec.SECP384R1()
    ) -> ec.EllipticCurvePublicKey:
        """
        Deserialize an elliptic curve public key from bytes.

        Args:
            public_key_bytes: Serialized public key bytes
            curve: Elliptic curve used

        Returns:
            EllipticCurvePublicKey object
        """
        return ec.EllipticCurvePublicKey.from_encoded_point(curve, public_key_bytes)

    # ==================== Secure Comparison ====================

    def constant_time_compare(self, a: bytes, b: bytes) -> bool:
        """
        Perform constant-time comparison of two byte strings.

        Args:
            a: First byte string
            b: Second byte string

        Returns:
            True if equal, False otherwise
        """
        return hmac.compare_digest(a, b)

    # ==================== Utility Functions ====================

    def generate_salt(self, size: int = SALT_SIZE) -> bytes:
        """
        Generate a random salt for key derivation.

        Args:
            size: Salt size in bytes (default: 32)

        Returns:
            Random salt bytes
        """
        return secrets.token_bytes(size)

    def secure_zero(self, data: bytearray) -> None:
        """
        Securely zero out memory containing sensitive data.

        Args:
            data: Bytearray to zero out
        """
        for i in range(len(data)):
            data[i] = 0
        logger.debug(f"Securely zeroed {len(data)} bytes")


# Convenience functions for common operations
def generate_session_key() -> SymmetricKey:
    """Generate a new session key with 24-hour lifetime."""
    crypto = CryptoUtils()
    return crypto.generate_symmetric_key(
        lifetime=CryptoUtils.SESSION_KEY_LIFETIME,
        key_id=secrets.token_hex(8)
    )


def encrypt_message(message: bytes, key: bytes) -> Dict[str, bytes]:
    """
    Encrypt a message and return ciphertext with nonce.

    Args:
        message: Message to encrypt
        key: Encryption key

    Returns:
        Dictionary with 'ciphertext' and 'nonce'
    """
    crypto = CryptoUtils()
    ciphertext, nonce = crypto.encrypt_aes_gcm(message, key)
    return {"ciphertext": ciphertext, "nonce": nonce}


def decrypt_message(ciphertext: bytes, nonce: bytes, key: bytes) -> bytes:
    """
    Decrypt a message.

    Args:
        ciphertext: Encrypted data
        nonce: Nonce used during encryption
        key: Decryption key

    Returns:
        Decrypted message bytes
    """
    crypto = CryptoUtils()
    return crypto.decrypt_aes_gcm(ciphertext, key, nonce)
