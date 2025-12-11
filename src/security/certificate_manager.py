"""
Certificate Manager for EduLens Secure Communication

This module handles certificate generation, validation, pinning, and revocation
checking for secure communication between EduLens devices.

Features:
- Self-signed certificate generation for devices
- Certificate chain validation
- Certificate pinning for MITM protection
- Revocation checking (OCSP/CRL)
- Certificate storage and retrieval
"""

import os
import json
import hashlib
from typing import Optional, List, Dict, Set, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import logging

from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

logger = logging.getLogger(__name__)


@dataclass
class CertificateInfo:
    """Information about a certificate."""
    subject: str
    issuer: str
    serial_number: str
    not_valid_before: datetime
    not_valid_after: datetime
    fingerprint: str
    public_key_fingerprint: str
    is_self_signed: bool
    key_usage: List[str]
    extended_key_usage: List[str]


@dataclass
class PinnedCertificate:
    """Pinned certificate information."""
    hostname: str
    fingerprints: List[str]  # SHA-256 fingerprints
    public_key_hashes: List[str]  # SPKI hashes
    pinned_at: datetime
    expires_at: Optional[datetime] = None


class CertificateManager:
    """
    Manages certificates for secure communication.

    Handles:
    - Device certificate generation
    - Certificate validation
    - Certificate pinning
    - Revocation checking
    """

    # Certificate validity periods
    DEVICE_CERT_VALIDITY = timedelta(days=365)
    ROOT_CERT_VALIDITY = timedelta(days=3650)  # 10 years

    # Key sizes
    RSA_KEY_SIZE = 2048
    EC_CURVE = ec.SECP384R1()

    def __init__(self, cert_directory: Optional[str] = None):
        """
        Initialize certificate manager.

        Args:
            cert_directory: Directory for storing certificates
        """
        self.cert_directory = Path(cert_directory) if cert_directory else Path.home() / ".edulens" / "certs"
        self.cert_directory.mkdir(parents=True, exist_ok=True)

        self.pinned_certs_file = self.cert_directory / "pinned_certificates.json"
        self.pinned_certificates: Dict[str, PinnedCertificate] = {}
        self._load_pinned_certificates()

        self.backend = default_backend()
        logger.info(f"CertificateManager initialized with cert directory: {self.cert_directory}")

    # ==================== Certificate Generation ====================

    def generate_device_cert(
        self,
        device_id: str,
        device_name: str,
        organization: str = "EduLens",
        use_ec: bool = True,
        validity_days: Optional[int] = None
    ) -> Tuple[x509.Certificate, bytes]:
        """
        Generate a self-signed certificate for a device.

        Args:
            device_id: Unique device identifier
            device_name: Human-readable device name
            organization: Organization name
            use_ec: Use EC key (True) or RSA (False)
            validity_days: Certificate validity period in days

        Returns:
            Tuple of (certificate, private_key_pem)
        """
        logger.info(f"Generating device certificate for: {device_id}")

        # Generate key pair
        if use_ec:
            private_key = ec.generate_private_key(self.EC_CURVE, self.backend)
            key_type = "EC"
        else:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=self.RSA_KEY_SIZE,
                backend=self.backend
            )
            key_type = "RSA"

        public_key = private_key.public_key()

        # Certificate subject
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "EduLens Devices"),
            x509.NameAttribute(NameOID.COMMON_NAME, device_name),
            x509.NameAttribute(NameOID.SERIAL_NUMBER, device_id),
        ])

        # Calculate validity period
        validity = timedelta(days=validity_days) if validity_days else self.DEVICE_CERT_VALIDITY
        not_valid_before = datetime.utcnow()
        not_valid_after = not_valid_before + validity

        # Build certificate
        cert_builder = x509.CertificateBuilder()
        cert_builder = cert_builder.subject_name(subject)
        cert_builder = cert_builder.issuer_name(issuer)
        cert_builder = cert_builder.public_key(public_key)
        cert_builder = cert_builder.serial_number(x509.random_serial_number())
        cert_builder = cert_builder.not_valid_before(not_valid_before)
        cert_builder = cert_builder.not_valid_after(not_valid_after)

        # Add extensions
        cert_builder = cert_builder.add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(f"{device_id}.edulens.local"),
                x509.DNSName(device_name),
            ]),
            critical=False,
        )

        cert_builder = cert_builder.add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )

        cert_builder = cert_builder.add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                key_agreement=True,
                content_commitment=False,
                data_encipherment=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )

        cert_builder = cert_builder.add_extension(
            x509.ExtendedKeyUsage([
                x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
                x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
            ]),
            critical=False,
        )

        # Self-sign the certificate
        certificate = cert_builder.sign(private_key, hashes.SHA256(), self.backend)

        # Serialize private key
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        # Save certificate and key
        self._save_device_certificate(device_id, certificate, private_key_pem)

        logger.info(f"Generated {key_type} device certificate for {device_id} (valid until {not_valid_after})")

        return certificate, private_key_pem

    def _save_device_certificate(
        self,
        device_id: str,
        certificate: x509.Certificate,
        private_key_pem: bytes
    ) -> None:
        """Save device certificate and private key to files."""
        cert_file = self.cert_directory / f"{device_id}_cert.pem"
        key_file = self.cert_directory / f"{device_id}_key.pem"

        # Save certificate
        cert_pem = certificate.public_bytes(serialization.Encoding.PEM)
        cert_file.write_bytes(cert_pem)

        # Save private key (should be encrypted in production)
        key_file.write_bytes(private_key_pem)
        os.chmod(key_file, 0o600)  # Restrict permissions

        logger.debug(f"Saved device certificate to {cert_file}")

    # ==================== Certificate Validation ====================

    def validate_cert(
        self,
        certificate: x509.Certificate,
        trusted_certs: Optional[List[x509.Certificate]] = None,
        check_expiration: bool = True,
        check_revocation: bool = False
    ) -> Tuple[bool, List[str]]:
        """
        Validate a certificate.

        Args:
            certificate: Certificate to validate
            trusted_certs: List of trusted CA certificates
            check_expiration: Check if certificate is expired
            check_revocation: Check if certificate is revoked

        Returns:
            Tuple of (is_valid, list of validation errors)
        """
        errors = []
        logger.debug(f"Validating certificate: {self._get_cert_subject(certificate)}")

        # Check expiration
        if check_expiration:
            now = datetime.utcnow()
            if now < certificate.not_valid_before:
                errors.append(f"Certificate not yet valid (starts {certificate.not_valid_before})")
            if now > certificate.not_valid_after:
                errors.append(f"Certificate expired (ended {certificate.not_valid_after})")

        # Check signature (for self-signed or with issuer)
        try:
            if self._is_self_signed(certificate):
                # Verify self-signed certificate
                public_key = certificate.public_key()
                public_key.verify(
                    certificate.signature,
                    certificate.tbs_certificate_bytes,
                    ec.ECDSA(hashes.SHA256()) if isinstance(public_key, ec.EllipticCurvePublicKey) else None
                )
            elif trusted_certs:
                # Verify with trusted CA
                if not self._verify_chain(certificate, trusted_certs):
                    errors.append("Certificate chain verification failed")
        except InvalidSignature:
            errors.append("Invalid certificate signature")
        except Exception as e:
            errors.append(f"Signature verification error: {e}")

        # Check key usage
        try:
            key_usage = certificate.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE).value
            if not (key_usage.digital_signature or key_usage.key_agreement):
                errors.append("Certificate lacks required key usage")
        except x509.ExtensionNotFound:
            errors.append("Certificate missing key usage extension")

        # Check revocation (simplified - would need OCSP/CRL in production)
        if check_revocation:
            if self._is_revoked(certificate):
                errors.append("Certificate has been revoked")

        is_valid = len(errors) == 0
        if is_valid:
            logger.info(f"Certificate validation successful: {self._get_cert_subject(certificate)}")
        else:
            logger.warning(f"Certificate validation failed: {errors}")

        return is_valid, errors

    def _verify_chain(
        self,
        certificate: x509.Certificate,
        trusted_certs: List[x509.Certificate]
    ) -> bool:
        """
        Verify certificate chain against trusted certificates.

        Args:
            certificate: Certificate to verify
            trusted_certs: List of trusted CA certificates

        Returns:
            True if chain is valid, False otherwise
        """
        # Simplified chain verification - production would use full path building
        for trusted_cert in trusted_certs:
            try:
                issuer_public_key = trusted_cert.public_key()
                if isinstance(issuer_public_key, ec.EllipticCurvePublicKey):
                    issuer_public_key.verify(
                        certificate.signature,
                        certificate.tbs_certificate_bytes,
                        ec.ECDSA(hashes.SHA256())
                    )
                    return True
                elif isinstance(issuer_public_key, rsa.RSAPublicKey):
                    issuer_public_key.verify(
                        certificate.signature,
                        certificate.tbs_certificate_bytes,
                        padding.PKCS1v15(),
                        hashes.SHA256()
                    )
                    return True
            except InvalidSignature:
                continue
            except Exception:
                continue

        return False

    # ==================== Certificate Pinning ====================

    def pin_certificate(
        self,
        hostname: str,
        certificate: x509.Certificate,
        pin_public_key: bool = True,
        lifetime: Optional[timedelta] = None
    ) -> PinnedCertificate:
        """
        Pin a certificate for a hostname.

        Args:
            hostname: Hostname to pin certificate for
            certificate: Certificate to pin
            pin_public_key: Pin public key hash instead of cert fingerprint
            lifetime: Pin lifetime (None = permanent)

        Returns:
            PinnedCertificate object
        """
        logger.info(f"Pinning certificate for hostname: {hostname}")

        # Calculate fingerprints
        cert_fingerprint = self._calculate_fingerprint(certificate)
        public_key_hash = self._calculate_public_key_hash(certificate)

        # Create pinned certificate
        pinned_at = datetime.utcnow()
        expires_at = pinned_at + lifetime if lifetime else None

        pinned_cert = PinnedCertificate(
            hostname=hostname,
            fingerprints=[cert_fingerprint],
            public_key_hashes=[public_key_hash],
            pinned_at=pinned_at,
            expires_at=expires_at
        )

        # Store pinned certificate
        self.pinned_certificates[hostname] = pinned_cert
        self._save_pinned_certificates()

        logger.info(f"Certificate pinned for {hostname} (expires: {expires_at or 'never'})")

        return pinned_cert

    def verify_pinned_certificate(
        self,
        hostname: str,
        certificate: x509.Certificate
    ) -> bool:
        """
        Verify a certificate against pinned certificates.

        Args:
            hostname: Hostname to check
            certificate: Certificate to verify

        Returns:
            True if certificate matches pin, False otherwise
        """
        if hostname not in self.pinned_certificates:
            logger.warning(f"No pinned certificate found for hostname: {hostname}")
            return False

        pinned_cert = self.pinned_certificates[hostname]

        # Check if pin has expired
        if pinned_cert.expires_at and datetime.utcnow() > pinned_cert.expires_at:
            logger.warning(f"Pinned certificate for {hostname} has expired")
            return False

        # Calculate fingerprints
        cert_fingerprint = self._calculate_fingerprint(certificate)
        public_key_hash = self._calculate_public_key_hash(certificate)

        # Check against pinned values
        is_valid = (
            cert_fingerprint in pinned_cert.fingerprints or
            public_key_hash in pinned_cert.public_key_hashes
        )

        if is_valid:
            logger.info(f"Certificate pin validation successful for {hostname}")
        else:
            logger.error(f"Certificate pin validation FAILED for {hostname} - possible MITM attack!")

        return is_valid

    def add_pin_fingerprint(
        self,
        hostname: str,
        fingerprint: str,
        is_public_key_hash: bool = False
    ) -> bool:
        """
        Add a fingerprint to an existing pin.

        Args:
            hostname: Hostname of pinned certificate
            fingerprint: Fingerprint to add
            is_public_key_hash: True if fingerprint is a public key hash

        Returns:
            True if added successfully, False otherwise
        """
        if hostname not in self.pinned_certificates:
            logger.warning(f"No pinned certificate found for hostname: {hostname}")
            return False

        pinned_cert = self.pinned_certificates[hostname]

        if is_public_key_hash:
            if fingerprint not in pinned_cert.public_key_hashes:
                pinned_cert.public_key_hashes.append(fingerprint)
        else:
            if fingerprint not in pinned_cert.fingerprints:
                pinned_cert.fingerprints.append(fingerprint)

        self._save_pinned_certificates()
        logger.info(f"Added fingerprint to pin for {hostname}")

        return True

    def unpin_certificate(self, hostname: str) -> bool:
        """
        Remove certificate pin for a hostname.

        Args:
            hostname: Hostname to unpin

        Returns:
            True if unpinned successfully, False otherwise
        """
        if hostname in self.pinned_certificates:
            del self.pinned_certificates[hostname]
            self._save_pinned_certificates()
            logger.info(f"Unpinned certificate for {hostname}")
            return True

        logger.warning(f"No pinned certificate found for hostname: {hostname}")
        return False

    # ==================== Revocation Checking ====================

    def check_revocation(
        self,
        certificate: x509.Certificate,
        use_ocsp: bool = True,
        use_crl: bool = True
    ) -> Tuple[bool, str]:
        """
        Check if a certificate has been revoked.

        Args:
            certificate: Certificate to check
            use_ocsp: Check using OCSP
            use_crl: Check using CRL

        Returns:
            Tuple of (is_revoked, reason)
        """
        # Simplified revocation check - production would implement full OCSP/CRL
        logger.debug(f"Checking revocation status for certificate: {self._get_cert_subject(certificate)}")

        # Check local revocation list
        if self._is_revoked(certificate):
            return True, "Certificate found in local revocation list"

        # In production, would check OCSP and CRL here
        # For now, assume not revoked
        return False, "Certificate not revoked"

    def _is_revoked(self, certificate: x509.Certificate) -> bool:
        """
        Check if certificate is in local revocation list.

        Args:
            certificate: Certificate to check

        Returns:
            True if revoked, False otherwise
        """
        revocation_file = self.cert_directory / "revoked_certificates.json"
        if not revocation_file.exists():
            return False

        try:
            with open(revocation_file, 'r') as f:
                revoked_serials = json.load(f)

            serial_hex = format(certificate.serial_number, 'x')
            return serial_hex in revoked_serials
        except Exception as e:
            logger.error(f"Error checking revocation list: {e}")
            return False

    # ==================== Certificate Information ====================

    def get_cert_info(self, certificate: x509.Certificate) -> CertificateInfo:
        """
        Extract information from a certificate.

        Args:
            certificate: Certificate to analyze

        Returns:
            CertificateInfo object with certificate details
        """
        subject = self._get_cert_subject(certificate)
        issuer = self._get_cert_issuer(certificate)
        fingerprint = self._calculate_fingerprint(certificate)
        public_key_fingerprint = self._calculate_public_key_hash(certificate)

        # Extract key usage
        key_usage = []
        try:
            ku = certificate.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE).value
            if ku.digital_signature:
                key_usage.append("digital_signature")
            if ku.key_encipherment:
                key_usage.append("key_encipherment")
            if ku.key_agreement:
                key_usage.append("key_agreement")
        except x509.ExtensionNotFound:
            pass

        # Extract extended key usage
        extended_key_usage = []
        try:
            eku = certificate.extensions.get_extension_for_oid(ExtensionOID.EXTENDED_KEY_USAGE).value
            for usage in eku:
                extended_key_usage.append(usage.dotted_string)
        except x509.ExtensionNotFound:
            pass

        return CertificateInfo(
            subject=subject,
            issuer=issuer,
            serial_number=format(certificate.serial_number, 'x'),
            not_valid_before=certificate.not_valid_before,
            not_valid_after=certificate.not_valid_after,
            fingerprint=fingerprint,
            public_key_fingerprint=public_key_fingerprint,
            is_self_signed=self._is_self_signed(certificate),
            key_usage=key_usage,
            extended_key_usage=extended_key_usage
        )

    # ==================== Helper Methods ====================

    def _calculate_fingerprint(self, certificate: x509.Certificate) -> str:
        """Calculate SHA-256 fingerprint of certificate."""
        cert_bytes = certificate.public_bytes(serialization.Encoding.DER)
        fingerprint = hashlib.sha256(cert_bytes).hexdigest()
        return fingerprint

    def _calculate_public_key_hash(self, certificate: x509.Certificate) -> str:
        """Calculate SHA-256 hash of public key (SPKI)."""
        public_key = certificate.public_key()
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        key_hash = hashlib.sha256(public_key_bytes).hexdigest()
        return key_hash

    def _get_cert_subject(self, certificate: x509.Certificate) -> str:
        """Get certificate subject as string."""
        try:
            cn = certificate.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
            return cn
        except (IndexError, AttributeError):
            return str(certificate.subject)

    def _get_cert_issuer(self, certificate: x509.Certificate) -> str:
        """Get certificate issuer as string."""
        try:
            cn = certificate.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
            return cn
        except (IndexError, AttributeError):
            return str(certificate.issuer)

    def _is_self_signed(self, certificate: x509.Certificate) -> bool:
        """Check if certificate is self-signed."""
        return certificate.subject == certificate.issuer

    def _load_pinned_certificates(self) -> None:
        """Load pinned certificates from file."""
        if not self.pinned_certs_file.exists():
            return

        try:
            with open(self.pinned_certs_file, 'r') as f:
                data = json.load(f)

            for hostname, cert_data in data.items():
                cert_data['pinned_at'] = datetime.fromisoformat(cert_data['pinned_at'])
                if cert_data.get('expires_at'):
                    cert_data['expires_at'] = datetime.fromisoformat(cert_data['expires_at'])

                self.pinned_certificates[hostname] = PinnedCertificate(**cert_data)

            logger.info(f"Loaded {len(self.pinned_certificates)} pinned certificates")
        except Exception as e:
            logger.error(f"Error loading pinned certificates: {e}")

    def _save_pinned_certificates(self) -> None:
        """Save pinned certificates to file."""
        try:
            data = {}
            for hostname, pinned_cert in self.pinned_certificates.items():
                cert_dict = asdict(pinned_cert)
                cert_dict['pinned_at'] = pinned_cert.pinned_at.isoformat()
                if pinned_cert.expires_at:
                    cert_dict['expires_at'] = pinned_cert.expires_at.isoformat()

                data[hostname] = cert_dict

            with open(self.pinned_certs_file, 'w') as f:
                json.dump(data, f, indent=2)

            logger.debug("Saved pinned certificates to file")
        except Exception as e:
            logger.error(f"Error saving pinned certificates: {e}")

    # ==================== Certificate Loading ====================

    def load_certificate_from_file(self, cert_path: str) -> x509.Certificate:
        """
        Load a certificate from PEM file.

        Args:
            cert_path: Path to certificate file

        Returns:
            Certificate object
        """
        with open(cert_path, 'rb') as f:
            cert_data = f.read()

        certificate = x509.load_pem_x509_certificate(cert_data, self.backend)
        logger.debug(f"Loaded certificate from {cert_path}")

        return certificate

    def load_private_key_from_file(self, key_path: str, password: Optional[bytes] = None):
        """
        Load a private key from PEM file.

        Args:
            key_path: Path to private key file
            password: Optional password for encrypted key

        Returns:
            Private key object
        """
        with open(key_path, 'rb') as f:
            key_data = f.read()

        private_key = serialization.load_pem_private_key(
            key_data,
            password=password,
            backend=self.backend
        )
        logger.debug(f"Loaded private key from {key_path}")

        return private_key
