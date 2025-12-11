"""
Device Pairing Protocol for EduLens

This module implements secure device pairing between EduLens glasses and
companion app using multiple methods including PIN codes, QR codes, and
Diffie-Hellman key exchange.

Security Features:
- 6-digit pairing codes with limited lifetime
- QR code-based pairing for convenience
- ECDH key exchange for shared secret
- Rate limiting and retry protection
- Pairing revocation and management
"""

import secrets
import time
import json
import qrcode
from io import BytesIO
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import logging

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature

from .crypto_utils import CryptoUtils

logger = logging.getLogger(__name__)


class PairingState(Enum):
    """States of the pairing process."""
    IDLE = "idle"
    CODE_GENERATED = "code_generated"
    WAITING_FOR_PEER = "waiting_for_peer"
    KEY_EXCHANGE = "key_exchange"
    VERIFYING = "verifying"
    PAIRED = "paired"
    FAILED = "failed"
    REVOKED = "revoked"


@dataclass
class PairingCode:
    """Pairing code information."""
    code: str
    device_id: str
    created_at: datetime
    expires_at: datetime
    attempts: int = 0
    max_attempts: int = 3


@dataclass
class PairedDevice:
    """Information about a paired device."""
    device_id: str
    device_name: str
    device_type: str  # "glasses" or "app"
    paired_at: datetime
    last_seen: Optional[datetime] = None
    shared_secret: Optional[bytes] = None
    public_key: Optional[bytes] = None
    metadata: Optional[Dict] = None


class PairingProtocol:
    """
    Secure device pairing protocol.

    Implements multiple pairing methods:
    1. PIN code pairing (6-digit code)
    2. QR code pairing
    3. NFC pairing (placeholder)

    All methods use ECDH for key exchange.
    """

    # Pairing configuration
    CODE_LENGTH = 6
    CODE_LIFETIME = timedelta(minutes=5)
    MAX_PAIRING_ATTEMPTS = 3
    RATE_LIMIT_WINDOW = timedelta(minutes=1)
    MAX_REQUESTS_PER_WINDOW = 5

    def __init__(self, device_id: str, device_name: str, device_type: str = "glasses"):
        """
        Initialize pairing protocol.

        Args:
            device_id: Unique device identifier
            device_name: Human-readable device name
            device_type: Type of device ("glasses" or "app")
        """
        self.device_id = device_id
        self.device_name = device_name
        self.device_type = device_type

        self.crypto = CryptoUtils()
        self.state = PairingState.IDLE

        # Pairing state
        self.active_codes: Dict[str, PairingCode] = {}
        self.paired_devices: Dict[str, PairedDevice] = {}
        self.pairing_requests: List[Tuple[str, datetime]] = []

        # Key exchange state
        self.ephemeral_key_pair: Optional[object] = None
        self.peer_public_key: Optional[bytes] = None
        self.shared_secret: Optional[bytes] = None

        logger.info(f"PairingProtocol initialized for device: {device_id} ({device_type})")

    # ==================== PIN Code Pairing ====================

    def generate_pairing_code(self) -> Tuple[str, datetime]:
        """
        Generate a 6-digit pairing code.

        Returns:
            Tuple of (pairing_code, expiration_time)
        """
        if not self._check_rate_limit():
            raise RuntimeError("Rate limit exceeded for pairing code generation")

        # Generate random 6-digit code
        code = ''.join([str(secrets.randbelow(10)) for _ in range(self.CODE_LENGTH)])

        # Create pairing code entry
        created_at = datetime.utcnow()
        expires_at = created_at + self.CODE_LIFETIME

        pairing_code = PairingCode(
            code=code,
            device_id=self.device_id,
            created_at=created_at,
            expires_at=expires_at,
            max_attempts=self.MAX_PAIRING_ATTEMPTS
        )

        self.active_codes[code] = pairing_code
        self.state = PairingState.CODE_GENERATED

        logger.info(f"Generated pairing code: {code} (expires at {expires_at})")

        # Clean up expired codes
        self._cleanup_expired_codes()

        return code, expires_at

    def verify_pairing_code(
        self,
        code: str,
        peer_device_id: str,
        peer_device_name: str,
        peer_device_type: str = "app"
    ) -> bool:
        """
        Verify a pairing code entered by peer device.

        Args:
            code: Pairing code to verify
            peer_device_id: ID of peer device
            peer_device_name: Name of peer device
            peer_device_type: Type of peer device

        Returns:
            True if code is valid, False otherwise
        """
        logger.info(f"Verifying pairing code: {code} from {peer_device_id}")

        if code not in self.active_codes:
            logger.warning(f"Invalid pairing code: {code}")
            return False

        pairing_code = self.active_codes[code]

        # Check expiration
        if datetime.utcnow() > pairing_code.expires_at:
            logger.warning(f"Pairing code expired: {code}")
            del self.active_codes[code]
            return False

        # Check attempts
        pairing_code.attempts += 1
        if pairing_code.attempts > pairing_code.max_attempts:
            logger.warning(f"Max pairing attempts exceeded for code: {code}")
            del self.active_codes[code]
            return False

        # Code is valid - remove from active codes
        del self.active_codes[code]
        self.state = PairingState.WAITING_FOR_PEER

        logger.info(f"Pairing code verified successfully for {peer_device_id}")

        return True

    # ==================== QR Code Pairing ====================

    def generate_pairing_qr(self, include_public_key: bool = True) -> bytes:
        """
        Generate a QR code for pairing.

        Args:
            include_public_key: Include public key in QR code

        Returns:
            QR code image as PNG bytes
        """
        logger.info("Generating pairing QR code")

        # Generate ephemeral key pair if needed
        if include_public_key:
            if not self.ephemeral_key_pair:
                self.ephemeral_key_pair = self.crypto.generate_key_pair()

            public_key_bytes = self.ephemeral_key_pair.serialize_public_key()
            public_key_hex = public_key_bytes.hex()
        else:
            public_key_hex = None

        # Generate pairing code
        code, expires_at = self.generate_pairing_code()

        # Create pairing data
        pairing_data = {
            "version": "1.0",
            "device_id": self.device_id,
            "device_name": self.device_name,
            "device_type": self.device_type,
            "code": code,
            "expires_at": expires_at.isoformat(),
            "public_key": public_key_hex
        }

        # Convert to JSON
        qr_content = json.dumps(pairing_data)

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_content)
        qr.make(fit=True)

        # Create image
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to bytes
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_bytes = buffer.getvalue()

        logger.info(f"Generated QR code for pairing (size: {len(qr_bytes)} bytes)")

        return qr_bytes

    def scan_pairing_qr(self, qr_data: str) -> Dict:
        """
        Process scanned QR code data.

        Args:
            qr_data: JSON string from scanned QR code

        Returns:
            Dictionary with pairing information
        """
        try:
            pairing_data = json.loads(qr_data)

            # Validate required fields
            required_fields = ["device_id", "device_name", "device_type", "code"]
            for field in required_fields:
                if field not in pairing_data:
                    raise ValueError(f"Missing required field: {field}")

            # Check expiration
            if "expires_at" in pairing_data:
                expires_at = datetime.fromisoformat(pairing_data["expires_at"])
                if datetime.utcnow() > expires_at:
                    raise ValueError("QR code has expired")

            # Extract public key if present
            if pairing_data.get("public_key"):
                self.peer_public_key = bytes.fromhex(pairing_data["public_key"])

            logger.info(f"Scanned QR code from device: {pairing_data['device_id']}")

            return pairing_data

        except json.JSONDecodeError as e:
            logger.error(f"Invalid QR code data format: {e}")
            raise ValueError("Invalid QR code format")
        except Exception as e:
            logger.error(f"Error processing QR code: {e}")
            raise

    # ==================== Key Exchange ====================

    def exchange_keys(
        self,
        peer_public_key_bytes: Optional[bytes] = None
    ) -> bytes:
        """
        Perform ECDH key exchange with peer device.

        Args:
            peer_public_key_bytes: Peer's public key (if not already set)

        Returns:
            Our public key bytes to send to peer
        """
        logger.info("Starting ECDH key exchange")

        # Generate ephemeral key pair if not already generated
        if not self.ephemeral_key_pair:
            self.ephemeral_key_pair = self.crypto.generate_key_pair(
                lifetime=timedelta(hours=1)
            )

        # Store peer's public key if provided
        if peer_public_key_bytes:
            self.peer_public_key = peer_public_key_bytes

        # Get our public key to send to peer
        our_public_key = self.ephemeral_key_pair.serialize_public_key()

        self.state = PairingState.KEY_EXCHANGE

        logger.debug(f"Generated ephemeral key pair (public key size: {len(our_public_key)} bytes)")

        return our_public_key

    def complete_key_exchange(self) -> bytes:
        """
        Complete ECDH key exchange and derive shared secret.

        Returns:
            Derived shared secret

        Raises:
            RuntimeError: If key exchange cannot be completed
        """
        if not self.ephemeral_key_pair:
            raise RuntimeError("Ephemeral key pair not generated")

        if not self.peer_public_key:
            raise RuntimeError("Peer public key not received")

        logger.info("Completing ECDH key exchange")

        # Deserialize peer's public key
        try:
            peer_public_key = self.crypto.deserialize_public_key(
                self.peer_public_key,
                curve=ec.SECP384R1()
            )
        except Exception as e:
            logger.error(f"Failed to deserialize peer public key: {e}")
            raise RuntimeError("Invalid peer public key")

        # Perform ECDH
        try:
            raw_shared_secret = self.crypto.perform_ecdh(
                self.ephemeral_key_pair.private_key,
                peer_public_key
            )
        except Exception as e:
            logger.error(f"ECDH failed: {e}")
            raise RuntimeError("Key exchange failed")

        # Derive shared secret using HKDF
        salt = self.crypto.generate_salt()
        self.shared_secret = self.crypto.derive_key(
            raw_shared_secret,
            salt=salt,
            info=b"edulens_pairing_v1",
            length=32
        )

        logger.info("ECDH key exchange completed successfully")

        return self.shared_secret

    # ==================== Pairing Completion ====================

    def complete_pairing(
        self,
        peer_device_id: str,
        peer_device_name: str,
        peer_device_type: str,
        peer_public_key: Optional[bytes] = None,
        metadata: Optional[Dict] = None
    ) -> PairedDevice:
        """
        Complete the pairing process and store paired device.

        Args:
            peer_device_id: ID of peer device
            peer_device_name: Name of peer device
            peer_device_type: Type of peer device
            peer_public_key: Peer's public key
            metadata: Additional device metadata

        Returns:
            PairedDevice object
        """
        logger.info(f"Completing pairing with device: {peer_device_id}")

        # Ensure key exchange is complete
        if not self.shared_secret:
            raise RuntimeError("Key exchange not completed")

        # Create paired device entry
        paired_device = PairedDevice(
            device_id=peer_device_id,
            device_name=peer_device_name,
            device_type=peer_device_type,
            paired_at=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            shared_secret=self.shared_secret,
            public_key=peer_public_key or self.peer_public_key,
            metadata=metadata or {}
        )

        # Store paired device
        self.paired_devices[peer_device_id] = paired_device
        self.state = PairingState.PAIRED

        # Clear ephemeral data
        self._clear_pairing_state()

        logger.info(f"Pairing completed successfully with {peer_device_id}")

        return paired_device

    def _clear_pairing_state(self) -> None:
        """Clear ephemeral pairing state data."""
        self.ephemeral_key_pair = None
        self.peer_public_key = None
        # Keep shared_secret as it's stored in paired device

    # ==================== Pairing Management ====================

    def revoke_pairing(self, device_id: str) -> bool:
        """
        Revoke pairing with a device.

        Args:
            device_id: ID of device to unpair

        Returns:
            True if revoked successfully, False otherwise
        """
        if device_id not in self.paired_devices:
            logger.warning(f"No paired device found with ID: {device_id}")
            return False

        # Remove from paired devices
        paired_device = self.paired_devices[device_id]
        del self.paired_devices[device_id]

        logger.info(f"Revoked pairing with device: {device_id} ({paired_device.device_name})")

        return True

    def get_paired_device(self, device_id: str) -> Optional[PairedDevice]:
        """
        Get information about a paired device.

        Args:
            device_id: ID of paired device

        Returns:
            PairedDevice object or None if not found
        """
        return self.paired_devices.get(device_id)

    def list_paired_devices(self) -> List[PairedDevice]:
        """
        Get list of all paired devices.

        Returns:
            List of PairedDevice objects
        """
        return list(self.paired_devices.values())

    def is_paired(self, device_id: str) -> bool:
        """
        Check if a device is paired.

        Args:
            device_id: ID of device to check

        Returns:
            True if paired, False otherwise
        """
        return device_id in self.paired_devices

    def update_last_seen(self, device_id: str) -> None:
        """
        Update last seen timestamp for a paired device.

        Args:
            device_id: ID of paired device
        """
        if device_id in self.paired_devices:
            self.paired_devices[device_id].last_seen = datetime.utcnow()

    # ==================== Rate Limiting ====================

    def _check_rate_limit(self) -> bool:
        """
        Check if rate limit is exceeded.

        Returns:
            True if within rate limit, False otherwise
        """
        now = datetime.utcnow()
        cutoff = now - self.RATE_LIMIT_WINDOW

        # Remove old requests
        self.pairing_requests = [
            (device_id, timestamp)
            for device_id, timestamp in self.pairing_requests
            if timestamp > cutoff
        ]

        # Check limit
        request_count = len(self.pairing_requests)
        if request_count >= self.MAX_REQUESTS_PER_WINDOW:
            logger.warning(f"Rate limit exceeded: {request_count} requests in {self.RATE_LIMIT_WINDOW}")
            return False

        # Add current request
        self.pairing_requests.append((self.device_id, now))

        return True

    def _cleanup_expired_codes(self) -> None:
        """Remove expired pairing codes."""
        now = datetime.utcnow()
        expired_codes = [
            code for code, data in self.active_codes.items()
            if now > data.expires_at
        ]

        for code in expired_codes:
            del self.active_codes[code]

        if expired_codes:
            logger.debug(f"Cleaned up {len(expired_codes)} expired pairing codes")

    # ==================== Persistence ====================

    def save_paired_devices(self, file_path: str) -> None:
        """
        Save paired devices to file.

        Args:
            file_path: Path to save file
        """
        try:
            data = {}
            for device_id, device in self.paired_devices.items():
                device_dict = asdict(device)
                # Convert datetime to ISO format
                device_dict['paired_at'] = device.paired_at.isoformat()
                if device.last_seen:
                    device_dict['last_seen'] = device.last_seen.isoformat()
                # Convert bytes to hex
                if device.shared_secret:
                    device_dict['shared_secret'] = device.shared_secret.hex()
                if device.public_key:
                    device_dict['public_key'] = device.public_key.hex()

                data[device_id] = device_dict

            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved {len(data)} paired devices to {file_path}")

        except Exception as e:
            logger.error(f"Error saving paired devices: {e}")
            raise

    def load_paired_devices(self, file_path: str) -> None:
        """
        Load paired devices from file.

        Args:
            file_path: Path to load file
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            for device_id, device_dict in data.items():
                # Convert ISO format to datetime
                device_dict['paired_at'] = datetime.fromisoformat(device_dict['paired_at'])
                if device_dict.get('last_seen'):
                    device_dict['last_seen'] = datetime.fromisoformat(device_dict['last_seen'])
                # Convert hex to bytes
                if device_dict.get('shared_secret'):
                    device_dict['shared_secret'] = bytes.fromhex(device_dict['shared_secret'])
                if device_dict.get('public_key'):
                    device_dict['public_key'] = bytes.fromhex(device_dict['public_key'])

                self.paired_devices[device_id] = PairedDevice(**device_dict)

            logger.info(f"Loaded {len(data)} paired devices from {file_path}")

        except FileNotFoundError:
            logger.info(f"No paired devices file found at {file_path}")
        except Exception as e:
            logger.error(f"Error loading paired devices: {e}")
            raise

    # ==================== Verification ====================

    def verify_paired_device(
        self,
        device_id: str,
        challenge: bytes,
        signature: bytes
    ) -> bool:
        """
        Verify a paired device using challenge-response.

        Args:
            device_id: ID of device to verify
            challenge: Challenge bytes
            signature: Signature of challenge

        Returns:
            True if verification successful, False otherwise
        """
        if device_id not in self.paired_devices:
            logger.warning(f"Device not paired: {device_id}")
            return False

        paired_device = self.paired_devices[device_id]

        if not paired_device.shared_secret:
            logger.error(f"No shared secret for device: {device_id}")
            return False

        # Verify HMAC signature
        expected_signature = self.crypto.compute_hmac(challenge, paired_device.shared_secret)

        is_valid = self.crypto.constant_time_compare(expected_signature, signature)

        if is_valid:
            logger.info(f"Device verification successful: {device_id}")
            self.update_last_seen(device_id)
        else:
            logger.warning(f"Device verification FAILED: {device_id}")

        return is_valid

    def create_challenge(self) -> bytes:
        """
        Create a random challenge for device verification.

        Returns:
            Random challenge bytes
        """
        return self.crypto.generate_random_bytes(32)

    def sign_challenge(self, challenge: bytes, device_id: str) -> bytes:
        """
        Sign a challenge for device verification.

        Args:
            challenge: Challenge bytes to sign
            device_id: ID of device we're proving identity to

        Returns:
            Signature bytes
        """
        if device_id not in self.paired_devices:
            raise ValueError(f"Device not paired: {device_id}")

        paired_device = self.paired_devices[device_id]

        if not paired_device.shared_secret:
            raise ValueError(f"No shared secret for device: {device_id}")

        # Sign with HMAC
        signature = self.crypto.compute_hmac(challenge, paired_device.shared_secret)

        return signature


# ==================== Helper Functions ====================

def format_pairing_code(code: str) -> str:
    """
    Format pairing code for display (XXX-XXX).

    Args:
        code: 6-digit pairing code

    Returns:
        Formatted code string
    """
    if len(code) != 6:
        return code

    return f"{code[:3]}-{code[3:]}"


def validate_pairing_code_format(code: str) -> bool:
    """
    Validate pairing code format.

    Args:
        code: Pairing code to validate

    Returns:
        True if valid format, False otherwise
    """
    # Remove formatting
    clean_code = code.replace("-", "").replace(" ", "")

    # Check length and digits
    return len(clean_code) == 6 and clean_code.isdigit()
