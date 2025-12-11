# EduLens Secure Communication Module

## Overview

The EduLens Security Module provides comprehensive security features for communication between EduLens smart glasses and companion applications. It implements industry-standard cryptographic protocols and security best practices to ensure data confidentiality, integrity, and authenticity.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Secure Communication                    │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Secure     │  │   Pairing    │  │ Certificate  │  │
│  │   Channel    │  │  Protocol    │  │   Manager    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                 │                  │          │
│         └─────────────────┴──────────────────┘          │
│                           │                             │
│                   ┌───────┴────────┐                    │
│                   │  Crypto Utils  │                    │
│                   └────────────────┘                    │
└─────────────────────────────────────────────────────────┘
```

## Components

### 1. Crypto Utils (`crypto_utils.py`)

Core cryptographic primitives and utilities.

**Features:**
- **Symmetric Encryption**: AES-256-GCM with authentication
- **Key Exchange**: ECDH with Curve25519/SECP384R1
- **Key Derivation**: HKDF (HMAC-based KDF)
- **Message Authentication**: HMAC-SHA256
- **Secure Random**: Cryptographically secure random generation

**Usage:**
```python
from security import CryptoUtils

crypto = CryptoUtils()

# Generate symmetric key
key = crypto.generate_symmetric_key()

# Encrypt data
ciphertext, nonce = crypto.encrypt_aes_gcm(
    plaintext=b"Secret message",
    key=key.key
)

# Decrypt data
plaintext = crypto.decrypt_aes_gcm(
    ciphertext=ciphertext,
    key=key.key,
    nonce=nonce
)
```

### 2. Certificate Manager (`certificate_manager.py`)

Handles certificate generation, validation, and pinning.

**Features:**
- **Self-signed Certificates**: For device authentication
- **Certificate Validation**: Chain validation and expiry checking
- **Certificate Pinning**: Protection against MITM attacks
- **Revocation Checking**: Support for OCSP/CRL

**Usage:**
```python
from security import CertificateManager

cert_manager = CertificateManager()

# Generate device certificate
cert, private_key = cert_manager.generate_device_cert(
    device_id="glasses_001",
    device_name="EduLens Glasses"
)

# Pin certificate for hostname
cert_manager.pin_certificate("api.edulens.com", cert)

# Verify pinned certificate
is_valid = cert_manager.verify_pinned_certificate("api.edulens.com", cert)
```

### 3. Pairing Protocol (`pairing_protocol.py`)

Implements secure device pairing with multiple methods.

**Features:**
- **PIN Code Pairing**: 6-digit pairing codes
- **QR Code Pairing**: Visual pairing for convenience
- **Key Exchange**: ECDH-based key agreement
- **Rate Limiting**: Protection against brute force
- **Pairing Management**: Revocation and device listing

**Usage:**
```python
from security import PairingProtocol

# Initialize pairing on glasses
glasses = PairingProtocol(
    device_id="glasses_001",
    device_name="EduLens Glasses",
    device_type="glasses"
)

# Generate pairing code
code, expires_at = glasses.generate_pairing_code()
print(f"Pairing code: {code}")

# On companion app - verify code
app = PairingProtocol(
    device_id="app_001",
    device_name="Companion App",
    device_type="app"
)

# Exchange keys
pub_key_glasses = glasses.exchange_keys()
pub_key_app = app.exchange_keys(pub_key_glasses)
glasses.exchange_keys(pub_key_app)

# Complete pairing
shared_secret = glasses.complete_key_exchange()
paired_device = glasses.complete_pairing(
    peer_device_id="app_001",
    peer_device_name="Companion App",
    peer_device_type="app"
)
```

### 4. Secure Channel (`secure_channel.py`)

End-to-end encrypted communication channel.

**Features:**
- **TLS 1.3**: Transport layer security
- **Perfect Forward Secrecy**: Ephemeral key exchange
- **Key Rotation**: Automatic periodic key updates
- **Replay Protection**: Sequence number tracking
- **MITM Protection**: Certificate pinning and mutual authentication

**Usage:**
```python
from security import SecureChannel, ChannelConfig

# Configure channel
config = ChannelConfig(
    use_tls=True,
    tls_version=ssl.TLSVersion.TLSv1_3,
    enable_pfs=True,
    key_rotation_interval=timedelta(hours=1)
)

# Create secure channel
channel = SecureChannel(
    device_id="glasses_001",
    device_name="EduLens Glasses",
    config=config
)

# Establish connection
channel.establish_connection(
    host="192.168.1.100",
    port=8443,
    peer_device_id="app_001"
)

# Send encrypted data
channel.send_encrypted(b"Hello, secure world!")

# Receive encrypted data
data = channel.receive_decrypted()

# Close channel
channel.close()
```

## Security Features

### End-to-End Encryption

All data transmitted between devices is encrypted using AES-256-GCM:
- **256-bit keys**: Maximum security level
- **GCM mode**: Authenticated encryption with additional data (AEAD)
- **Unique nonces**: 96-bit random nonces prevent replay attacks

### Perfect Forward Secrecy (PFS)

Each session uses ephemeral keys:
- **ECDH key exchange**: Temporary keys for each session
- **Key rotation**: Periodic key updates during long sessions
- **No key compromise**: Past communications remain secure even if current keys are compromised

### Certificate Pinning

Protects against MITM attacks:
- **Public key pinning**: Pin public key hashes instead of full certificates
- **Backup pins**: Support for key rotation without service disruption
- **Expiration**: Automatic pin expiration and renewal

### Attack Protection

#### MITM (Man-in-the-Middle) Protection
- Mutual authentication using certificates
- Certificate pinning for cloud services
- Public key verification during pairing

#### Replay Attack Protection
- Sequence number tracking
- Timestamp verification
- Nonce-based message authentication

#### Timing Attack Protection
- Constant-time comparisons
- Fixed-time operations where possible
- No information leakage through timing

#### Downgrade Attack Protection
- Minimum TLS version enforcement (TLS 1.2+)
- Cipher suite restrictions
- Protocol version negotiation

## Configuration

Configure security settings via `/configs/security/communication_config.yaml`:

```yaml
tls:
  enabled: true
  version: "TLS_1_3"
  cipher_suites:
    - "TLS_AES_256_GCM_SHA384"

encryption:
  algorithm: "AES_256_GCM"
  key_size: 256

key_rotation:
  enabled: true
  rotation_interval_hours: 1

pairing:
  code_length: 6
  code_lifetime_minutes: 5
  max_pairing_attempts: 3
```

## Testing

Run comprehensive security tests:

```bash
cd /Users/anuppandey/Desktop/edu_lens
python tests/security/test_secure_communication.py
```

Test coverage includes:
- Cryptographic primitive validation
- Certificate generation and validation
- Pairing protocol flows
- Secure channel operations
- Attack resistance testing
- Integration scenarios

## Dependencies

Required Python packages:
- `cryptography>=41.0.0` - Cryptographic primitives
- `qrcode>=7.4.0` - QR code generation for pairing
- `PyYAML>=6.0` - Configuration file parsing

Install dependencies:
```bash
pip install cryptography qrcode pyyaml
```

## Best Practices

### Key Management
1. **Never hardcode keys** - Always generate keys dynamically
2. **Rotate keys regularly** - Use automatic key rotation
3. **Secure key storage** - Use OS keychain or hardware security modules
4. **Clear sensitive data** - Zero out memory after use

### Certificate Management
1. **Use certificate pinning** for all cloud services
2. **Monitor certificate expiration** - Renew before expiry
3. **Revoke compromised certificates** immediately
4. **Use strong key algorithms** - EC preferred over RSA

### Pairing
1. **Use QR codes** when possible for better UX
2. **Enforce rate limiting** to prevent brute force
3. **Set short code lifetimes** (5 minutes recommended)
4. **Require re-pairing** after extended disconnection

### Communication
1. **Always use TLS 1.3** for transport encryption
2. **Enable Perfect Forward Secrecy**
3. **Implement key rotation** for long-lived connections
4. **Validate peer identity** on every connection

## Security Auditing

Enable security audit logging:

```yaml
audit:
  enable_audit_log: true
  audit_log_file: "~/.edulens/logs/security_audit.log"
  audit_events:
    - "pairing_request"
    - "authentication_failure"
    - "key_rotation"
    - "security_violation"
```

## Compliance

The module is designed to support:
- **GDPR**: Data protection and privacy by design
- **HIPAA**: Healthcare data security (when properly configured)
- **PCI DSS**: Payment security standards
- **NIST**: Cryptographic standards compliance

## Performance

Typical performance metrics (on modern hardware):

| Operation | Time | Throughput |
|-----------|------|------------|
| AES-256-GCM Encryption | ~1 µs/KB | ~1 GB/s |
| ECDH Key Exchange | ~2 ms | 500 exchanges/s |
| Certificate Validation | ~5 ms | 200 validations/s |
| Message Authentication | ~0.5 µs/KB | ~2 GB/s |

## Troubleshooting

### Connection Fails
1. Check TLS configuration matches on both sides
2. Verify certificates are valid and not expired
3. Ensure certificate pinning hashes are correct
4. Check firewall and network connectivity

### Pairing Fails
1. Verify pairing code hasn't expired
2. Check rate limiting hasn't been triggered
3. Ensure devices support same cryptographic algorithms
4. Verify network connectivity between devices

### Encryption Errors
1. Ensure keys match on both sides
2. Verify sequence numbers are synchronized
3. Check for message tampering or corruption
4. Validate nonce uniqueness

## Future Enhancements

Planned features:
- **Quantum-resistant algorithms**: Post-quantum cryptography (PQC)
- **Hardware security module (HSM)** integration
- **Zero-knowledge proofs** for privacy-preserving authentication
- **NFC pairing** support
- **Biometric authentication** integration

## Contributing

When contributing security code:
1. Follow secure coding guidelines
2. Add comprehensive tests for all new features
3. Document security properties and assumptions
4. Conduct security review before merging
5. Update threat model documentation

## License

Copyright (c) 2025 EduLens Security Team. All rights reserved.

## Contact

For security issues, contact: security@edulens.com

For security vulnerabilities, please follow responsible disclosure:
1. Do NOT create public GitHub issues
2. Email security@edulens.com with details
3. Allow 90 days for patch before disclosure
4. Receive credit in security advisories
