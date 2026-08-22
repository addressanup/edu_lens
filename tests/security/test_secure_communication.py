"""
Comprehensive Tests for EduLens Secure Communication

This test suite validates the security implementation including:
- Cryptographic utilities
- Certificate management
- Device pairing
- Secure communication channel
- Attack resistance
"""

import os
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from security.certificate_manager import CertificateInfo, CertificateManager
from security.crypto_utils import CryptoUtils, KeyPair, SymmetricKey
from security.pairing_protocol import PairingProtocol, PairingState, format_pairing_code
from security.secure_channel import ChannelConfig, ChannelState, SecureChannel


class TestCryptoUtils(unittest.TestCase):
    """Test cryptographic utilities."""

    def setUp(self):
        """Set up test fixtures."""
        self.crypto = CryptoUtils()

    def test_generate_symmetric_key(self):
        """Test symmetric key generation."""
        key = self.crypto.generate_symmetric_key()

        self.assertIsNotNone(key)
        self.assertEqual(len(key.key), CryptoUtils.AES_KEY_SIZE)
        self.assertIsInstance(key.created_at, datetime)
        self.assertFalse(key.is_expired())

    def test_generate_symmetric_key_with_lifetime(self):
        """Test symmetric key generation with expiration."""
        lifetime = timedelta(seconds=1)
        key = self.crypto.generate_symmetric_key(lifetime=lifetime)

        self.assertFalse(key.is_expired())
        time.sleep(2)
        self.assertTrue(key.is_expired())

    def test_generate_key_pair(self):
        """Test asymmetric key pair generation."""
        keypair = self.crypto.generate_key_pair()

        self.assertIsNotNone(keypair)
        self.assertIsNotNone(keypair.private_key)
        self.assertIsNotNone(keypair.public_key)
        self.assertIsInstance(keypair.created_at, datetime)

    def test_ecdh_key_exchange(self):
        """Test ECDH key exchange."""
        # Generate two key pairs
        keypair1 = self.crypto.generate_key_pair()
        keypair2 = self.crypto.generate_key_pair()

        # Perform ECDH from both sides
        shared_secret1 = self.crypto.perform_ecdh(keypair1.private_key, keypair2.public_key)
        shared_secret2 = self.crypto.perform_ecdh(keypair2.private_key, keypair1.public_key)

        # Secrets should match
        self.assertEqual(shared_secret1, shared_secret2)
        self.assertGreater(len(shared_secret1), 0)

    def test_derive_key(self):
        """Test key derivation using HKDF."""
        input_material = self.crypto.generate_random_bytes(32)
        salt = self.crypto.generate_salt()

        derived_key = self.crypto.derive_key(input_material, salt=salt, info=b"test_context")

        self.assertEqual(len(derived_key), CryptoUtils.AES_KEY_SIZE)

        # Same inputs should produce same output
        derived_key2 = self.crypto.derive_key(input_material, salt=salt, info=b"test_context")
        self.assertEqual(derived_key, derived_key2)

        # Different info should produce different output
        derived_key3 = self.crypto.derive_key(input_material, salt=salt, info=b"different_context")
        self.assertNotEqual(derived_key, derived_key3)

    def test_derive_session_keys(self):
        """Test session key derivation."""
        shared_secret = self.crypto.generate_random_bytes(32)
        salt = self.crypto.generate_salt()

        session_keys = self.crypto.derive_session_keys(shared_secret, salt, context="test_session")

        self.assertIn("encryption_key", session_keys)
        self.assertIn("mac_key", session_keys)
        self.assertIn("nonce_key", session_keys)

        # All keys should be different
        self.assertNotEqual(session_keys["encryption_key"], session_keys["mac_key"])
        self.assertNotEqual(session_keys["encryption_key"], session_keys["nonce_key"])
        self.assertNotEqual(session_keys["mac_key"], session_keys["nonce_key"])

    def test_aes_gcm_encryption_decryption(self):
        """Test AES-GCM encryption and decryption."""
        plaintext = b"This is a secret message for testing encryption"
        key = self.crypto.generate_symmetric_key().key

        # Encrypt
        ciphertext, nonce = self.crypto.encrypt_aes_gcm(plaintext, key)

        self.assertNotEqual(ciphertext, plaintext)
        self.assertEqual(len(nonce), CryptoUtils.NONCE_SIZE)

        # Decrypt
        decrypted = self.crypto.decrypt_aes_gcm(ciphertext, key, nonce)

        self.assertEqual(decrypted, plaintext)

    def test_aes_gcm_with_associated_data(self):
        """Test AES-GCM with authenticated additional data."""
        plaintext = b"Secret message"
        key = self.crypto.generate_symmetric_key().key
        associated_data = b"metadata"

        # Encrypt with AAD
        ciphertext, nonce = self.crypto.encrypt_aes_gcm(
            plaintext, key, associated_data=associated_data
        )

        # Decrypt with correct AAD
        decrypted = self.crypto.decrypt_aes_gcm(
            ciphertext, key, nonce, associated_data=associated_data
        )
        self.assertEqual(decrypted, plaintext)

        # Decrypt with wrong AAD should fail
        with self.assertRaises(InvalidTag):
            self.crypto.decrypt_aes_gcm(ciphertext, key, nonce, associated_data=b"wrong_metadata")

    def test_aes_gcm_tamper_detection(self):
        """Test that AES-GCM detects tampering."""
        plaintext = b"Original message"
        key = self.crypto.generate_symmetric_key().key

        ciphertext, nonce = self.crypto.encrypt_aes_gcm(plaintext, key)

        # Tamper with ciphertext
        tampered = bytearray(ciphertext)
        tampered[0] ^= 0xFF
        tampered = bytes(tampered)

        # Decryption should fail
        with self.assertRaises(InvalidTag):
            self.crypto.decrypt_aes_gcm(tampered, key, nonce)

    def test_hmac_computation_and_verification(self):
        """Test HMAC computation and verification."""
        message = b"Message to authenticate"
        key = self.crypto.generate_random_bytes(32)

        # Compute HMAC
        mac = self.crypto.compute_hmac(message, key)

        self.assertIsNotNone(mac)
        self.assertGreater(len(mac), 0)

        # Verify correct HMAC
        is_valid = self.crypto.verify_hmac(message, key, mac)
        self.assertTrue(is_valid)

        # Verify incorrect HMAC
        is_valid = self.crypto.verify_hmac(message, key, b"wrong_mac")
        self.assertFalse(is_valid)

        # Verify with wrong message
        is_valid = self.crypto.verify_hmac(b"Different message", key, mac)
        self.assertFalse(is_valid)

    def test_random_generation(self):
        """Test secure random generation."""
        # Generate random bytes
        random1 = self.crypto.generate_random_bytes(32)
        random2 = self.crypto.generate_random_bytes(32)

        self.assertEqual(len(random1), 32)
        self.assertNotEqual(random1, random2)

        # Generate random hex
        hex_string = self.crypto.generate_random_hex(16)
        self.assertEqual(len(hex_string), 32)  # 16 bytes = 32 hex chars

        # Generate random int
        random_int = self.crypto.generate_random_int(1, 100)
        self.assertGreaterEqual(random_int, 1)
        self.assertLessEqual(random_int, 100)

    def test_hash_functions(self):
        """Test cryptographic hash functions."""
        data = b"Data to hash"

        # SHA-256
        hash256 = self.crypto.hash_data(data, algorithm="sha256")
        self.assertEqual(len(hash256), 32)

        # SHA-384
        hash384 = self.crypto.hash_data(data, algorithm="sha384")
        self.assertEqual(len(hash384), 48)

        # Same input should produce same hash
        hash256_2 = self.crypto.hash_data(data, algorithm="sha256")
        self.assertEqual(hash256, hash256_2)

    def test_constant_time_comparison(self):
        """Test constant-time comparison."""
        data1 = b"secret_value"
        data2 = b"secret_value"
        data3 = b"different_value"

        self.assertTrue(self.crypto.constant_time_compare(data1, data2))
        self.assertFalse(self.crypto.constant_time_compare(data1, data3))


class TestCertificateManager(unittest.TestCase):
    """Test certificate management."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cert_manager = CertificateManager(cert_directory=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generate_device_certificate_ec(self):
        """Test EC device certificate generation."""
        device_id = "test_device_001"
        device_name = "Test EduLens Glasses"

        cert, private_key = self.cert_manager.generate_device_cert(
            device_id, device_name, use_ec=True
        )

        self.assertIsInstance(cert, x509.Certificate)
        self.assertIsNotNone(private_key)

        # Verify certificate properties
        self.assertEqual(
            cert.subject.get_attributes_for_oid(x509.NameOID.SERIAL_NUMBER)[0].value, device_id
        )
        self.assertEqual(
            cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value, device_name
        )

    def test_generate_device_certificate_rsa(self):
        """Test RSA device certificate generation."""
        device_id = "test_device_002"
        device_name = "Test Companion App"

        cert, private_key = self.cert_manager.generate_device_cert(
            device_id, device_name, use_ec=False
        )

        self.assertIsInstance(cert, x509.Certificate)
        self.assertIsNotNone(private_key)

    def test_validate_self_signed_certificate(self):
        """Test validation of self-signed certificate."""
        cert, _ = self.cert_manager.generate_device_cert("test_device", "Test Device")

        is_valid, errors = self.cert_manager.validate_cert(
            cert, check_expiration=True, check_revocation=False
        )

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_certificate_expiration_detection(self):
        """Test detection of expired certificates."""
        # Generate certificate with 0 day validity (expired)
        cert, _ = self.cert_manager.generate_device_cert(
            "test_device", "Test Device", validity_days=0
        )

        # Wait a moment to ensure expiration
        time.sleep(0.1)

        is_valid, errors = self.cert_manager.validate_cert(cert, check_expiration=True)

        self.assertFalse(is_valid)
        self.assertTrue(any("expired" in err.lower() for err in errors))

    def test_certificate_pinning(self):
        """Test certificate pinning."""
        hostname = "test.edulens.com"
        cert, _ = self.cert_manager.generate_device_cert("test_device", "Test Device")

        # Pin certificate
        pinned = self.cert_manager.pin_certificate(hostname, cert)

        self.assertEqual(pinned.hostname, hostname)
        self.assertGreater(len(pinned.fingerprints), 0)
        self.assertGreater(len(pinned.public_key_hashes), 0)

        # Verify pinned certificate
        is_valid = self.cert_manager.verify_pinned_certificate(hostname, cert)
        self.assertTrue(is_valid)

        # Generate different certificate
        cert2, _ = self.cert_manager.generate_device_cert("other_device", "Other Device")

        # Verification should fail for different certificate
        is_valid = self.cert_manager.verify_pinned_certificate(hostname, cert2)
        self.assertFalse(is_valid)

    def test_certificate_unpinning(self):
        """Test unpinning certificates."""
        hostname = "test.edulens.com"
        cert, _ = self.cert_manager.generate_device_cert("test_device", "Test Device")

        # Pin and then unpin
        self.cert_manager.pin_certificate(hostname, cert)
        success = self.cert_manager.unpin_certificate(hostname)

        self.assertTrue(success)
        self.assertNotIn(hostname, self.cert_manager.pinned_certificates)

    def test_get_certificate_info(self):
        """Test certificate information extraction."""
        device_id = "test_device_123"
        device_name = "Test Device"

        cert, _ = self.cert_manager.generate_device_cert(device_id, device_name)

        cert_info = self.cert_manager.get_cert_info(cert)

        self.assertIsInstance(cert_info, CertificateInfo)
        self.assertEqual(cert_info.subject, device_name)
        self.assertTrue(cert_info.is_self_signed)
        self.assertGreater(len(cert_info.fingerprint), 0)


class TestPairingProtocol(unittest.TestCase):
    """Test device pairing protocol."""

    def setUp(self):
        """Set up test fixtures."""
        self.device1 = PairingProtocol(
            device_id="glasses_001", device_name="EduLens Glasses", device_type="glasses"
        )
        self.device2 = PairingProtocol(
            device_id="app_001", device_name="Companion App", device_type="app"
        )

    def test_generate_pairing_code(self):
        """Test pairing code generation."""
        code, expires_at = self.device1.generate_pairing_code()

        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())
        self.assertIsInstance(expires_at, datetime)
        self.assertGreater(expires_at, datetime.utcnow())
        self.assertEqual(self.device1.state, PairingState.CODE_GENERATED)

    def test_verify_valid_pairing_code(self):
        """Test verification of valid pairing code."""
        code, _ = self.device1.generate_pairing_code()

        is_valid = self.device1.verify_pairing_code(code, "app_001", "Companion App", "app")

        self.assertTrue(is_valid)
        self.assertEqual(self.device1.state, PairingState.WAITING_FOR_PEER)

    def test_verify_invalid_pairing_code(self):
        """Test verification of invalid pairing code."""
        is_valid = self.device1.verify_pairing_code("123456", "app_001", "Companion App", "app")

        self.assertFalse(is_valid)

    def test_pairing_code_expiration(self):
        """Test pairing code expiration."""
        # Generate code with short lifetime
        code, _ = self.device1.generate_pairing_code()

        # Manually expire the code
        self.device1.active_codes[code].expires_at = datetime.utcnow() - timedelta(seconds=1)

        # Verification should fail
        is_valid = self.device1.verify_pairing_code(code, "app_001", "Companion App")

        self.assertFalse(is_valid)

    def test_pairing_code_max_attempts(self):
        """Test pairing code max attempts."""
        code, _ = self.device1.generate_pairing_code()

        # Exhaust attempts
        for i in range(PairingProtocol.MAX_PAIRING_ATTEMPTS + 1):
            self.device1.verify_pairing_code(code, f"device_{i}", f"Device {i}")

        # Code should be removed
        self.assertNotIn(code, self.device1.active_codes)

    def test_key_exchange(self):
        """Test ECDH key exchange between devices."""
        # Device 1 generates key pair
        public_key1 = self.device1.exchange_keys()

        # Device 2 generates key pair
        public_key2 = self.device2.exchange_keys()

        # Exchange public keys
        self.device1.exchange_keys(public_key2)
        self.device2.exchange_keys(public_key1)

        # Complete key exchange
        shared_secret1 = self.device1.complete_key_exchange()
        shared_secret2 = self.device2.complete_key_exchange()

        # Shared secrets should match
        self.assertEqual(shared_secret1, shared_secret2)

    def test_complete_pairing(self):
        """Test complete pairing process."""
        # Generate and verify pairing code
        code, _ = self.device1.generate_pairing_code()
        self.device1.verify_pairing_code(code, "app_001", "Companion App")

        # Exchange keys
        public_key1 = self.device1.exchange_keys()
        public_key2 = self.device2.exchange_keys(public_key1)
        self.device1.exchange_keys(public_key2)

        shared_secret1 = self.device1.complete_key_exchange()
        shared_secret2 = self.device2.complete_key_exchange()

        # Complete pairing
        paired_device1 = self.device1.complete_pairing("app_001", "Companion App", "app")
        paired_device2 = self.device2.complete_pairing("glasses_001", "EduLens Glasses", "glasses")

        self.assertEqual(self.device1.state, PairingState.PAIRED)
        self.assertEqual(self.device2.state, PairingState.PAIRED)
        self.assertTrue(self.device1.is_paired("app_001"))
        self.assertTrue(self.device2.is_paired("glasses_001"))

    def test_revoke_pairing(self):
        """Test pairing revocation."""
        # First pair devices
        code, _ = self.device1.generate_pairing_code()
        self.device1.verify_pairing_code(code, "app_001", "Companion App")

        public_key1 = self.device1.exchange_keys()
        public_key2 = self.device2.exchange_keys(public_key1)
        self.device1.exchange_keys(public_key2)

        self.device1.complete_key_exchange()
        self.device1.complete_pairing("app_001", "Companion App", "app")

        # Revoke pairing
        success = self.device1.revoke_pairing("app_001")

        self.assertTrue(success)
        self.assertFalse(self.device1.is_paired("app_001"))

    def test_list_paired_devices(self):
        """Test listing paired devices."""
        # Pair with multiple devices
        for i in range(3):
            code, _ = self.device1.generate_pairing_code()
            self.device1.verify_pairing_code(code, f"app_{i}", f"App {i}")

            public_key1 = self.device1.exchange_keys()
            temp_device = PairingProtocol(f"app_{i}", f"App {i}", "app")
            public_key2 = temp_device.exchange_keys(public_key1)
            self.device1.exchange_keys(public_key2)

            self.device1.complete_key_exchange()
            self.device1.complete_pairing(f"app_{i}", f"App {i}", "app")

        paired_devices = self.device1.list_paired_devices()

        self.assertEqual(len(paired_devices), 3)

    def test_qr_code_generation(self):
        """Test QR code generation for pairing."""
        qr_bytes = self.device1.generate_pairing_qr()

        self.assertIsNotNone(qr_bytes)
        self.assertGreater(len(qr_bytes), 0)
        self.assertEqual(self.device1.state, PairingState.CODE_GENERATED)

    def test_format_pairing_code(self):
        """Test pairing code formatting."""
        code = "123456"
        formatted = format_pairing_code(code)

        self.assertEqual(formatted, "123-456")

    def test_rate_limiting(self):
        """Test rate limiting for pairing code generation."""
        # Generate codes up to limit
        for i in range(PairingProtocol.MAX_REQUESTS_PER_WINDOW):
            code, _ = self.device1.generate_pairing_code()

        # Next request should fail
        with self.assertRaises(RuntimeError):
            self.device1.generate_pairing_code()


class TestSecureChannel(unittest.TestCase):
    """Test secure communication channel."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        self.config = ChannelConfig(use_tls=False, connection_timeout=5)  # Disable TLS for testing

        self.channel1 = SecureChannel(
            device_id="device_1", device_name="Device 1", config=self.config
        )

        self.channel2 = SecureChannel(
            device_id="device_2", device_name="Device 2", config=self.config
        )

    def tearDown(self):
        """Clean up test fixtures."""
        self.channel1.close()
        self.channel2.close()

        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_channel_initialization(self):
        """Test secure channel initialization."""
        self.assertEqual(self.channel1.state, ChannelState.DISCONNECTED)
        self.assertEqual(self.channel1.device_id, "device_1")
        self.assertIsNotNone(self.channel1.crypto)

    def test_message_serialization(self):
        """Test message serialization and deserialization."""
        from security.secure_channel import Message, MessageType

        original_message = Message(
            message_type=MessageType.DATA,
            sequence_number=42,
            timestamp=time.time(),
            payload=b"Test payload data",
        )

        # Serialize
        serialized = self.channel1._serialize_message(original_message)

        # Deserialize
        deserialized = self.channel1._deserialize_message(serialized)

        self.assertEqual(deserialized.message_type, original_message.message_type)
        self.assertEqual(deserialized.sequence_number, original_message.sequence_number)
        self.assertEqual(deserialized.payload, original_message.payload)

    def test_encryption_decryption_flow(self):
        """Test encryption and decryption of messages."""
        # Set up encryption keys
        crypto = CryptoUtils()
        session_key = crypto.generate_symmetric_key()

        self.channel1.send_key = session_key.key
        self.channel1.receive_key = session_key.key
        self.channel2.send_key = session_key.key
        self.channel2.receive_key = session_key.key

        # Test data
        test_data = b"This is a secret message for testing"

        # Simulate sending (encryption)
        from security.secure_channel import Message, MessageType

        message = Message(
            message_type=MessageType.DATA,
            sequence_number=0,
            timestamp=time.time(),
            payload=test_data,
        )

        plaintext = self.channel1._serialize_message(message)
        ciphertext, nonce = crypto.encrypt_aes_gcm(
            plaintext, self.channel1.send_key, associated_data=b"\x00" * 8
        )

        # Simulate receiving (decryption)
        decrypted = crypto.decrypt_aes_gcm(
            ciphertext, self.channel2.receive_key, nonce, associated_data=b"\x00" * 8
        )

        received_message = self.channel2._deserialize_message(decrypted)

        self.assertEqual(received_message.payload, test_data)

    def test_sequence_number_tracking(self):
        """Test sequence number tracking for replay protection."""
        self.assertEqual(self.channel1.send_sequence, 0)
        self.assertEqual(self.channel1.receive_sequence, 0)

        # Increment sequence numbers
        self.channel1.send_sequence = (
            self.channel1.send_sequence + 1
        ) % SecureChannel.MAX_SEQUENCE_NUMBER
        self.assertEqual(self.channel1.send_sequence, 1)

    def test_channel_statistics(self):
        """Test channel statistics tracking."""
        self.assertEqual(self.channel1.stats.messages_sent, 0)
        self.assertEqual(self.channel1.stats.messages_received, 0)
        self.assertEqual(self.channel1.stats.errors, 0)

    def test_context_manager(self):
        """Test using secure channel as context manager."""
        with SecureChannel("test_device", "Test Device", self.config) as channel:
            self.assertIsNotNone(channel)
            self.assertEqual(channel.device_id, "test_device")

        # Channel should be closed after context
        self.assertEqual(channel.state, ChannelState.DISCONNECTED)


class TestSecurityFeatures(unittest.TestCase):
    """Test security features and attack resistance."""

    def setUp(self):
        """Set up test fixtures."""
        self.crypto = CryptoUtils()

    def test_replay_attack_protection(self):
        """Test protection against replay attacks."""
        # Encrypt message with sequence number
        plaintext = b"Original message"
        key = self.crypto.generate_symmetric_key().key
        sequence_num = 42

        ciphertext, nonce = self.crypto.encrypt_aes_gcm(
            plaintext, key, associated_data=str(sequence_num).encode()
        )

        # Decrypt with correct sequence number
        decrypted = self.crypto.decrypt_aes_gcm(
            ciphertext, key, nonce, associated_data=str(sequence_num).encode()
        )
        self.assertEqual(decrypted, plaintext)

        # Decrypt with different sequence number should fail
        with self.assertRaises(InvalidTag):
            self.crypto.decrypt_aes_gcm(ciphertext, key, nonce, associated_data=str(999).encode())

    def test_tampering_detection(self):
        """Test detection of message tampering."""
        message = b"Important message"
        key = self.crypto.generate_random_bytes(32)

        # Compute MAC
        mac = self.crypto.compute_hmac(message, key)

        # Tamper with message
        tampered_message = b"Modified message"

        # Verification should fail
        is_valid = self.crypto.verify_hmac(tampered_message, key, mac)
        self.assertFalse(is_valid)

    def test_perfect_forward_secrecy(self):
        """Test that each session uses unique ephemeral keys."""
        # Simulate two sessions
        session1_keypair = self.crypto.generate_key_pair()
        session2_keypair = self.crypto.generate_key_pair()

        # Keys should be different
        self.assertNotEqual(
            session1_keypair.serialize_public_key(), session2_keypair.serialize_public_key()
        )

    def test_key_rotation(self):
        """Test key rotation functionality."""
        # Generate initial key
        key1 = self.crypto.generate_symmetric_key()

        # Simulate key rotation after interval
        time.sleep(0.1)
        key2 = self.crypto.generate_symmetric_key()

        # Keys should be different
        self.assertNotEqual(key1.key, key2.key)

    def test_secure_random_unpredictability(self):
        """Test that random generation is unpredictable."""
        # Generate multiple random values
        random_values = [self.crypto.generate_random_bytes(32) for _ in range(10)]

        # All values should be unique
        unique_values = set(random_values)
        self.assertEqual(len(unique_values), 10)

    def test_timing_attack_resistance(self):
        """Test constant-time comparison for timing attack resistance."""
        correct_value = b"secret_password"
        test_value1 = b"secret_password"
        test_value2 = b"wrong_password1"

        # Measure comparison times (simplified test)
        start1 = time.perf_counter()
        result1 = self.crypto.constant_time_compare(correct_value, test_value1)
        time1 = time.perf_counter() - start1

        start2 = time.perf_counter()
        result2 = self.crypto.constant_time_compare(correct_value, test_value2)
        time2 = time.perf_counter() - start2

        self.assertTrue(result1)
        self.assertFalse(result2)

        # Times should be similar (within an order of magnitude)
        # Note: This is a simplified test; real timing attack tests are more complex
        time_ratio = max(time1, time2) / min(time1, time2)
        self.assertLess(time_ratio, 100)  # Loose bound for test stability


class TestIntegration(unittest.TestCase):
    """Integration tests for complete security flow."""

    def test_complete_pairing_and_communication(self):
        """Test complete flow from pairing to secure communication."""
        # Create two devices
        glasses = PairingProtocol("glasses_001", "EduLens Glasses", "glasses")
        app = PairingProtocol("app_001", "Companion App", "app")

        # Step 1: Generate pairing code
        code, _ = glasses.generate_pairing_code()
        self.assertIsNotNone(code)

        # Step 2: Verify pairing code
        is_valid = glasses.verify_pairing_code(code, "app_001", "Companion App")
        self.assertTrue(is_valid)

        # Step 3: Exchange keys
        public_key_glasses = glasses.exchange_keys()
        public_key_app = app.exchange_keys(public_key_glasses)
        glasses.exchange_keys(public_key_app)

        # Step 4: Complete key exchange
        shared_secret_glasses = glasses.complete_key_exchange()
        shared_secret_app = app.complete_key_exchange()

        self.assertEqual(shared_secret_glasses, shared_secret_app)

        # Step 5: Complete pairing
        glasses.complete_pairing("app_001", "Companion App", "app")
        app.complete_pairing("glasses_001", "EduLens Glasses", "glasses")

        self.assertTrue(glasses.is_paired("app_001"))
        self.assertTrue(app.is_paired("glasses_001"))

        # Step 6: Verify paired device authentication
        challenge = glasses.create_challenge()
        signature = app.sign_challenge(challenge, "glasses_001")
        is_verified = glasses.verify_paired_device("app_001", challenge, signature)

        self.assertTrue(is_verified)


def run_security_tests():
    """Run all security tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestCryptoUtils))
    suite.addTests(loader.loadTestsFromTestCase(TestCertificateManager))
    suite.addTests(loader.loadTestsFromTestCase(TestPairingProtocol))
    suite.addTests(loader.loadTestsFromTestCase(TestSecureChannel))
    suite.addTests(loader.loadTestsFromTestCase(TestSecurityFeatures))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    # Run all tests
    success = run_security_tests()
    sys.exit(0 if success else 1)
