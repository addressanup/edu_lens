"""
EduLens Security Module

This module provides secure communication capabilities for EduLens devices,
including end-to-end encryption, device pairing, certificate management,
and protection against various security threats.

Main Components:
- crypto_utils: Cryptographic primitives and utilities
- certificate_manager: Certificate generation, validation, and pinning
- pairing_protocol: Secure device pairing with multiple methods
- secure_channel: End-to-end encrypted communication channel

Security Features:
- AES-256-GCM encryption
- Perfect Forward Secrecy (PFS)
- TLS 1.3 support
- Certificate pinning
- MITM attack protection
- Replay attack protection
- Key rotation
"""

from .crypto_utils import CryptoUtils, SymmetricKey, KeyPair
from .certificate_manager import CertificateManager, CertificateInfo, PinnedCertificate
from .pairing_protocol import PairingProtocol, PairingState, PairedDevice, format_pairing_code
from .secure_channel import SecureChannel, ChannelState, ChannelConfig, MessageType

__version__ = "1.0.0"
__author__ = "EduLens Security Team"

__all__ = [
    # Crypto utilities
    "CryptoUtils",
    "SymmetricKey",
    "KeyPair",

    # Certificate management
    "CertificateManager",
    "CertificateInfo",
    "PinnedCertificate",

    # Pairing protocol
    "PairingProtocol",
    "PairingState",
    "PairedDevice",
    "format_pairing_code",

    # Secure channel
    "SecureChannel",
    "ChannelState",
    "ChannelConfig",
    "MessageType",
]
