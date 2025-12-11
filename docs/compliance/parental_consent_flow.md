# EduLens Parental Consent Flow Documentation

**Document:** Parental Consent Collection and Management
**Classification:** SECURITY CRITICAL - COPPA COMPLIANCE
**Version:** 1.0
**Last Updated:** December 10, 2025
**Owner:** Security and Privacy Agent (SEC-001)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Consent Collection Process](#2-consent-collection-process)
3. [Verification Methods](#3-verification-methods)
4. [Consent Revocation](#4-consent-revocation)
5. [Record Keeping](#5-record-keeping)
6. [Technical Implementation](#6-technical-implementation)
7. [Compliance Requirements](#7-compliance-requirements)

---

## 1. Overview

### 1.1 Purpose

This document describes EduLens's parental consent collection, verification, and management processes to ensure compliance with the Children's Online Privacy Protection Act (COPPA) 16 CFR Part 312.

### 1.2 Legal Basis

**COPPA Requirement (16 CFR 312.5):**
Operators must obtain verifiable parental consent before collecting, using, or disclosing personal information from children under 13.

**EduLens Approach:**
- Multiple FTC-approved verification methods
- Clear, comprehensive consent notices
- Easy consent revocation
- Detailed audit trail
- Annual consent renewal

### 1.3 Consent Principles

1. **Informed Consent:** Parents receive complete information before consenting
2. **Granular Consent:** Separate consent for different data categories
3. **Easy Revocation:** One-click consent withdrawal
4. **Verifiable Identity:** Multiple verification methods ensure parent authenticity
5. **Audit Trail:** Immutable record of all consent actions

---

## 2. Consent Collection Process

### 2.1 Process Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     PARENTAL CONSENT FLOW                            │
└─────────────────────────────────────────────────────────────────────┘

START: Parent Creates Account
        ↓
┌───────────────────────────────┐
│ 1. Parent Registration        │
│ - Email address               │
│ - Password (secure)           │
│ - Age verification (18+)      │
└───────────────────────────────┘
        ↓
┌───────────────────────────────┐
│ 2. Email Verification         │
│ - Send verification link      │
│ - Parent clicks link          │
│ - Email confirmed             │
└───────────────────────────────┘
        ↓
┌───────────────────────────────┐
│ 3. Child Profile Setup        │
│ - Child pseudonym (NOT name)  │
│ - Child age range             │
│ - Grade level (optional)      │
└───────────────────────────────┘
        ↓
┌───────────────────────────────┐
│ 4. Privacy Policy Presentation│
│ - Full privacy policy shown   │
│ - Key points highlighted      │
│ - "What data is collected"    │
│ - "How data is protected"     │
│ - "Your rights as parent"     │
└───────────────────────────────┘
        ↓
┌───────────────────────────────┐
│ 5. Consent Notice Display     │
│ - Granular consent options    │
│ - Required vs Optional data   │
│ - Consequences explained      │
│ - "I understand" checkboxes   │
└───────────────────────────────┘
        ↓
┌───────────────────────────────┐
│ 6. Verifiable Consent Method  │
│ OPTION A: Credit Card         │
│ - $0.50 verification charge   │
│ - Immediate refund            │
│                               │
│ OPTION B: Multi-Factor Auth   │
│ - Email + SMS verification    │
│ - Government ID upload        │
└───────────────────────────────┘
        ↓
┌───────────────────────────────┐
│ 7. Consent Confirmation       │
│ - Verification successful     │
│ - Consent recorded            │
│ - Confirmation email sent     │
│ - Consent ID generated        │
└───────────────────────────────┘
        ↓
┌───────────────────────────────┐
│ 8. Account Activation         │
│ - Full app access enabled     │
│ - Parent dashboard available  │
│ - Consent expiry: 365 days    │
└───────────────────────────────┘
        ↓
END: App Ready for Child Use
```

### 2.2 Step-by-Step Process

#### Step 1: Parent Registration

**Screen:** Account Creation

**Information Collected:**
- Parent email address (required)
- Secure password (required)
- Age confirmation checkbox: "I am 18 years or older" (required)

**Validation:**
- Email format validation
- Password strength requirements (12+ characters, mixed case, numbers, symbols)
- Age checkbox must be checked

**Duration:** 2-3 minutes

**Technical Flow:**
```python
POST /api/v1/auth/register
{
    "email": "parent@example.com",
    "password": "SecurePass123!",
    "age_verified": true,
    "terms_accepted": true
}

Response:
{
    "account_id": "uuid-v4",
    "status": "pending_email_verification",
    "verification_sent": true
}
```

#### Step 2: Email Verification

**Screen:** Email Sent Confirmation

**Process:**
1. System sends verification email with unique token (expires in 24 hours)
2. Parent clicks verification link in email
3. System validates token and marks email as verified

**Security:**
- Token: Cryptographically secure random 256-bit value
- One-time use (invalidated after click)
- Expiration: 24 hours
- IP address logged for fraud detection

**Technical Flow:**
```python
GET /api/v1/auth/verify-email?token=<verification_token>

Response:
{
    "email_verified": true,
    "account_status": "email_verified",
    "next_step": "child_profile_setup"
}
```

#### Step 3: Child Profile Setup

**Screen:** Create Child Profile

**Information Collected:**
- Child pseudonym: A nickname or label (NOT real name)
  - Examples: "My First Grader", "Math Student", "Learner 1"
- Child age range: Dropdown with ranges (5-7, 8-10, 11-13)
- Grade level: Optional (K-8)

**Guidance Provided:**
- "Do NOT use your child's real name"
- "Choose a nickname or label like 'Student 1'"
- "We use this only to show you which child's data you're managing"

**Technical Flow:**
```python
POST /api/v1/children/create
{
    "parent_account_id": "uuid-v4",
    "pseudonym": "My Math Student",
    "age_range": "8-10",
    "grade_level": 3
}

Response:
{
    "child_id": "uuid-v4",
    "pseudonym": "My Math Student",
    "status": "created"
}
```

#### Step 4: Privacy Policy Presentation

**Screen:** Privacy Policy Review

**Content:**
- Full privacy policy (linked document)
- Key highlights summary box:
  - "We do NOT store photos or voice recordings"
  - "We do NOT collect your child's name"
  - "We do NOT share data with third parties"
  - "You can revoke consent anytime"

**Requirements:**
- Parent must scroll through entire document
- "I have read and understand" checkbox
- Link to full policy: /privacy-policy

**Duration:** 5-10 minutes (required reading time)

#### Step 5: Consent Notice Display

**Screen:** Grant Permissions

**Consent Categories:**

**REQUIRED (for basic functionality):**

1. **Device Operation**
   - Processing camera images on-device (immediate deletion)
   - Processing voice commands on-device (immediate deletion)
   - Temporary session storage (deleted on app close)
   - Consequence if denied: App cannot function

2. **Parental Account Management**
   - Store your (parent) email and account information
   - Send you service updates and notifications
   - Process subscription payments
   - Consequence if denied: Cannot create account

**OPTIONAL (can opt out):**

3. **Anonymous Telemetry**
   - Collect anonymous usage statistics
   - Identify and fix bugs
   - Improve app performance
   - Consequence if denied: No impact on functionality

4. **Aggregated Research**
   - Use anonymized data for educational research
   - Improve tutoring algorithms
   - Contribute to educational technology advancement
   - Consequence if denied: No impact on functionality

**Presentation:**
- Each category has detailed explanation
- Visual indicators: Required (lock icon) vs Optional (toggle switch)
- Estimated reading time: 10-15 minutes

**Technical Flow:**
```python
POST /api/v1/consent/categories
{
    "parent_account_id": "uuid-v4",
    "child_id": "uuid-v4",
    "consent_selections": {
        "device_operation": "required",
        "parental_account": "required",
        "anonymous_telemetry": "optional_selected",
        "aggregated_research": "optional_declined"
    }
}

Response:
{
    "selections_saved": true,
    "next_step": "verification"
}
```

#### Step 6: Verifiable Consent Method

**Screen:** Verify Your Identity

**Option A: Credit Card Verification (Primary Method)**

**Process:**
1. Parent enters credit card information
2. System charges $0.50 verification fee
3. Charge is processed (confirms adult with financial instrument)
4. Charge is immediately refunded (within 24-48 hours)
5. Consent verified

**Security:**
- PCI DSS Level 1 compliant payment processor
- Card details never stored by EduLens
- Only last 4 digits saved for reference

**FTC Compliance:**
- Approved method under 16 CFR 312.5(b)(2)
- "Credit card, debit card, or other online payment system"

**Technical Flow:**
```python
POST /api/v1/consent/verify/credit-card
{
    "parent_account_id": "uuid-v4",
    "payment_token": "stripe_token_xyz",  # From Stripe.js
    "billing_zip": "12345"
}

Response:
{
    "verification_successful": true,
    "charge_id": "ch_xyz",
    "refund_id": "re_xyz",
    "consent_verified": true,
    "consent_id": "consent_uuid"
}
```

**Option B: Multi-Factor Authentication + ID (Secondary Method)**

**Process:**
1. Parent receives email verification code (6-digit)
2. Parent receives SMS verification code (6-digit)
3. Parent uploads photo of government-issued ID (optional, for enhanced verification)
4. Both codes must be entered within 30 minutes
5. Consent verified

**Security:**
- Email and phone must match account registration
- Codes expire after 30 minutes
- Maximum 3 attempts
- ID verification performed by identity verification service (e.g., Jumio, Onfido)

**FTC Compliance:**
- Email + Knowledge-based authentication combination
- Enhanced with SMS and optional ID for added security

**Technical Flow:**
```python
# Step 1: Request verification codes
POST /api/v1/consent/verify/mfa/initiate
{
    "parent_account_id": "uuid-v4",
    "phone_number": "+1234567890"
}

Response:
{
    "email_sent": true,
    "sms_sent": true,
    "expires_at": "2025-12-10T15:30:00Z"
}

# Step 2: Submit verification codes
POST /api/v1/consent/verify/mfa/confirm
{
    "parent_account_id": "uuid-v4",
    "email_code": "123456",
    "sms_code": "789012"
}

Response:
{
    "verification_successful": true,
    "consent_verified": true,
    "consent_id": "consent_uuid"
}
```

#### Step 7: Consent Confirmation

**Screen:** Consent Confirmed

**Actions:**
1. Generate unique consent ID
2. Create immutable consent record
3. Send confirmation email to parent
4. Log consent in audit trail
5. Set consent expiration date (365 days from now)

**Confirmation Email Contains:**
- Consent ID
- Date and time of consent
- What was consented to
- Expiration date
- How to revoke consent
- Parent dashboard link

**Technical Flow:**
```python
# System creates ConsentRecord
ConsentRecord {
    consent_id: "consent_8f7e9d2c",
    parent_account_id: "parent_uuid",
    child_pseudonym: "My Math Student",
    category: DataClassification.DEVICE_OPERATION,
    status: ConsentStatus.GRANTED,
    timestamp: "2025-12-10T14:00:00Z",
    consent_method: "CREDIT_CARD",
    verification_method: "STRIPE_VERIFICATION",
    expires_at: "2026-12-10T14:00:00Z",
    ip_address_hash: "sha256_hash_of_ip",
    metadata: {
        user_agent: "Mozilla/5.0...",
        verification_amount: 0.50,
        refund_processed: true
    }
}

# Send confirmation email
POST /api/v1/notifications/consent-confirmation
{
    "parent_email": "parent@example.com",
    "consent_id": "consent_8f7e9d2c",
    "template": "consent_confirmed"
}
```

#### Step 8: Account Activation

**Screen:** Welcome to EduLens!

**Actions:**
1. Enable full app access
2. Provide parent dashboard access
3. Display getting started guide
4. Enable child device pairing

**Parent Dashboard Features:**
- View consent status
- Manage consent preferences
- Revoke consent (one-click)
- View child's usage summary (anonymous stats only)
- Update account settings
- Access support resources

---

## 3. Verification Methods

### 3.1 Credit Card Verification (Primary)

**FTC Classification:** Approved method under 16 CFR 312.5(b)(2)

**Advantages:**
- Verifies adult status (requires financial instrument)
- Industry-standard verification method
- Low friction for parents
- Instant verification

**Process:**
1. Parent enters credit card information via secure payment form
2. Payment processor (Stripe/Braintree) tokenizes card
3. System authorizes $0.50 charge
4. Charge captures (proves card is valid and has adult authorization)
5. System immediately processes refund
6. Consent verified and recorded

**Security Measures:**
- PCI DSS Level 1 compliant processing
- No card details stored by EduLens
- 3D Secure / AVS verification
- Fraud detection algorithms
- SSL/TLS encryption for all communications

**Parent Communication:**
- Clear notice that charge will be refunded
- Explanation of why verification is needed
- Refund timeline: 24-48 hours
- Charge description: "EduLens Parent Verification - Refunded"

### 3.2 Multi-Factor Authentication (Secondary)

**FTC Classification:** Combination of email + knowledge-based authentication

**Advantages:**
- No financial transaction required
- Suitable for parents without credit cards
- Multiple verification factors

**Process:**
1. Email verification code (6-digit, expires 30 min)
2. SMS verification code (6-digit, expires 30 min)
3. Both codes must be entered correctly
4. Optional: Government ID photo upload for enhanced verification

**Security Measures:**
- Rate limiting: Max 3 attempts per hour
- Code generation: Cryptographically secure random
- One-time use codes
- IP address monitoring for fraud
- Account lockout after 5 failed attempts

**Limitations:**
- Suitable for internal operations only (per FTC guidance)
- Requires email + phone number verification
- Cannot be used for third-party data sharing scenarios

### 3.3 Alternative Verification Methods (Future)

**Video Conference Verification:**
- Live video call with parent
- Show government ID to staff member
- Staff verifies identity
- Labor-intensive, high-touch

**Notarized Consent Form:**
- Parent signs consent form before notary
- Notary verifies identity and witness signature
- Form mailed or scanned to EduLens
- Slow, but highest verification level

**Digital Signature Services:**
- Use services like DocuSign with ID verification
- Multi-factor authentication + ID check
- Electronic signature with timestamp
- Moderate cost per verification

---

## 4. Consent Revocation

### 4.1 Revocation Process

**Parent Rights:**
- Revoke consent at any time
- No questions asked
- No penalties or fees
- Immediate effect

**Revocation Methods:**

#### Method 1: In-App Revocation (Instant)

**Process:**
1. Parent logs into parent dashboard
2. Navigate to: Settings > Privacy > Consent Management
3. Click "Revoke Consent" button for specific category
4. Confirmation dialog: "Are you sure? This will delete [description]"
5. Parent confirms revocation
6. System immediately processes revocation

**Timeline:** Instant (< 1 second)

**Technical Flow:**
```python
POST /api/v1/consent/revoke
{
    "parent_account_id": "uuid-v4",
    "child_id": "uuid-v4",
    "consent_id": "consent_8f7e9d2c",
    "reason": "optional_reason_text"
}

Response:
{
    "revocation_successful": true,
    "consent_status": "REVOKED",
    "data_deletion_initiated": true,
    "deletion_task_id": "del_task_uuid"
}
```

#### Method 2: Email Request (24-hour processing)

**Process:**
1. Parent emails privacy@edulens.com with subject "Revoke Consent"
2. Email must include:
   - Parent account email
   - Consent ID (from confirmation email)
   - Confirmation: "I want to revoke consent for..."
3. Privacy team verifies identity
4. Consent revoked within 24 hours
5. Confirmation email sent to parent

**Timeline:** Within 24 business hours

#### Method 3: Phone Request (48-hour processing)

**Process:**
1. Parent calls 1-800-EDU-LENS
2. Customer service representative verifies identity:
   - Parent email
   - Last 4 digits of payment card
   - Account creation date
3. Representative initiates revocation process
4. Consent revoked within 48 hours
5. Confirmation email sent to parent

**Timeline:** Within 48 business hours

### 4.2 Consequences of Revocation

**Data Deletion:**
- All associated data is immediately scheduled for deletion
- Deletion task created and tracked
- Verification performed after deletion
- Deletion log entry created

**App Functionality:**
- Device-only features continue to work (no cloud data required)
- Cloud-dependent features disabled
- Parental dashboard access maintained
- Re-consent option available anytime

**Account Status:**
- Account remains active (parent access)
- Child profile set to "consent_revoked" status
- No new data collection permitted
- Historical consent records retained for compliance (7 years)

### 4.3 Re-Consent Process

**Parents can re-consent at any time:**

1. Log into parent dashboard
2. Navigate to: Settings > Privacy > Consent Management
3. Click "Grant Consent" for revoked category
4. Review updated privacy policy (if changed)
5. Complete verification again (credit card or MFA)
6. New consent record created
7. App functionality restored

**Technical Flow:**
```python
POST /api/v1/consent/re-grant
{
    "parent_account_id": "uuid-v4",
    "child_id": "uuid-v4",
    "previous_consent_id": "consent_8f7e9d2c",
    "category": "DEVICE_OPERATION",
    "verification_method": "CREDIT_CARD"
}

Response:
{
    "consent_granted": true,
    "new_consent_id": "consent_9g8h0e3d",
    "status": "GRANTED",
    "expires_at": "2026-12-10T15:00:00Z"
}
```

---

## 5. Record Keeping

### 5.1 Consent Record Structure

Every consent action creates an immutable audit record:

```python
@dataclass
class ConsentRecord:
    """Immutable record of parental consent."""

    # Identifiers
    consent_id: str                    # Unique consent identifier
    parent_account_id: str             # Parent account
    child_pseudonym: str               # Child pseudonym (NOT real name)

    # Consent details
    category: DataClassification       # What category was consented to
    status: ConsentStatus              # GRANTED/DENIED/REVOKED/EXPIRED

    # Timestamps
    timestamp: datetime                # When consent was granted
    expires_at: Optional[datetime]     # When consent expires (365 days)
    revoked_at: Optional[datetime]     # When consent was revoked (if applicable)

    # Verification
    consent_method: str                # "CREDIT_CARD" | "MFA_EMAIL_SMS"
    verification_method: str           # Detailed verification method
    ip_address_hash: Optional[str]     # SHA-256 hash of IP (fraud prevention)

    # Audit trail
    metadata: Dict[str, Any]           # Additional context

    def is_valid(self) -> bool:
        """Check if consent is currently valid."""
        return (
            self.status == ConsentStatus.GRANTED and
            (not self.expires_at or datetime.utcnow() <= self.expires_at) and
            not self.revoked_at
        )
```

### 5.2 Storage and Retention

**Storage:**
- Database: PostgreSQL with row-level encryption
- Encryption: AES-256-GCM
- Backup: Daily encrypted backups, 7-year retention
- Access: Restricted to authorized personnel only
- Audit: All access logged

**Retention:**
- Active consents: Retained while valid
- Expired consents: Retained for 7 years (COPPA requirement)
- Revoked consents: Retained for 7 years (COPPA requirement)
- Denied consents: Retained for 7 years (COPPA requirement)

**Legal Basis:**
- COPPA requires operators to maintain consent records
- FTC may request consent records during audits
- 7-year retention period is industry standard for compliance

### 5.3 Audit Trail

Every consent-related action generates an audit log entry:

```python
AuditLogEntry {
    log_id: "uuid-v4",
    action: "CONSENT_GRANTED" | "CONSENT_REVOKED" | "CONSENT_EXPIRED",
    parent_account_id: "uuid-v4",
    child_id: "uuid-v4",
    consent_id: "consent_8f7e9d2c",
    timestamp: "2025-12-10T14:00:00Z",
    ip_address_hash: "sha256_hash",
    user_agent: "Mozilla/5.0...",
    details: {
        category: "DEVICE_OPERATION",
        method: "CREDIT_CARD",
        result: "SUCCESS"
    }
}
```

**Audit Log Characteristics:**
- Immutable: Cannot be edited or deleted
- Tamper-proof: Cryptographic checksums
- Timestamped: ISO 8601 UTC timestamps
- Comprehensive: All consent actions logged
- Retained: 7 years minimum

### 5.4 Parental Access to Records

**Parents can access their consent records at any time:**

**In-App Access:**
1. Parent dashboard > Privacy > Consent History
2. View all current consents
3. View consent history (granted, revoked, expired)
4. Download consent records (JSON or PDF)

**Email Request:**
1. Email privacy@edulens.com with "Consent Records Request"
2. Identity verification performed
3. Records emailed within 48 hours

**Data Provided:**
- Consent ID
- Date/time of consent
- What was consented to
- Verification method used
- Current status (active/revoked/expired)
- Expiration date
- Revocation date (if applicable)

---

## 6. Technical Implementation

### 6.1 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   CONSENT MANAGEMENT SYSTEM                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────┐         ┌─────────────────┐
│   Parent App    │◄───────►│  API Gateway    │
│   (Frontend)    │         │  (HTTPS/SSL)    │
└─────────────────┘         └─────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ↓                ↓                ↓
         ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
         │   Consent    │  │  Payment     │  │ Notification │
         │   Service    │  │  Service     │  │   Service    │
         └──────────────┘  └──────────────┘  └──────────────┘
                │                 │                  │
                ↓                 ↓                  ↓
         ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
         │  DataHandler │  │   Stripe     │  │   SendGrid   │
         │   (Privacy)  │  │   (PCI-DSS)  │  │   (Email)    │
         └──────────────┘  └──────────────┘  └──────────────┘
                │
                ↓
         ┌──────────────┐
         │  PostgreSQL  │
         │  (Encrypted) │
         └──────────────┘
                │
                ↓
         ┌──────────────┐
         │  Audit Log   │
         │  (Immutable) │
         └──────────────┘
```

### 6.2 API Endpoints

**Consent Management API:**

```python
# Grant consent
POST /api/v1/consent/grant
Request: { parent_id, child_id, category, verification_method }
Response: { consent_id, status, expires_at }

# Revoke consent
POST /api/v1/consent/revoke
Request: { parent_id, child_id, consent_id, reason }
Response: { revocation_successful, deletion_initiated }

# Check consent status
GET /api/v1/consent/status/{parent_id}/{child_id}/{category}
Response: { consent_id, status, expires_at, is_valid }

# Get consent history
GET /api/v1/consent/history/{parent_id}
Response: { consents: [...] }

# Renew consent
POST /api/v1/consent/renew
Request: { parent_id, consent_id, verification_method }
Response: { new_consent_id, status, expires_at }
```

### 6.3 Database Schema

```sql
CREATE TABLE consent_records (
    consent_id VARCHAR(36) PRIMARY KEY,
    parent_account_id VARCHAR(36) NOT NULL,
    child_pseudonym VARCHAR(255) NOT NULL,
    category VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    consent_method VARCHAR(64) NOT NULL,
    verification_method VARCHAR(255) NOT NULL,
    ip_address_hash VARCHAR(64),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    INDEX idx_parent_child (parent_account_id, child_pseudonym),
    INDEX idx_status (status),
    INDEX idx_expires_at (expires_at)
);

CREATE TABLE consent_audit_log (
    log_id VARCHAR(36) PRIMARY KEY,
    consent_id VARCHAR(36) NOT NULL,
    action VARCHAR(64) NOT NULL,
    parent_account_id VARCHAR(36) NOT NULL,
    child_id VARCHAR(36),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    ip_address_hash VARCHAR(64),
    user_agent TEXT,
    details JSONB,

    INDEX idx_consent_id (consent_id),
    INDEX idx_parent (parent_account_id),
    INDEX idx_timestamp (timestamp)
);
```

---

## 7. Compliance Requirements

### 7.1 COPPA Requirements Checklist

| Requirement | Implementation | Status |
|-------------|----------------|--------|
| Direct notice to parents (312.4(c)) | Privacy policy + consent notice | ✅ COMPLIANT |
| Verifiable parental consent (312.5) | Credit card + MFA methods | ✅ COMPLIANT |
| Parent access rights (312.6) | Parent dashboard + API access | ✅ COMPLIANT |
| Conditional access (312.7) | No excess data required | ✅ COMPLIANT |
| Data security (312.8) | Encryption + audit logging | ✅ COMPLIANT |
| Consent withdrawal (312.6(a)(2)) | One-click revocation | ✅ COMPLIANT |
| Record retention (compliance) | 7-year audit trail | ✅ COMPLIANT |

### 7.2 FTC Verification Method Approval

**Credit Card Method:**
- FTC Approved: 16 CFR 312.5(b)(2)
- "Credit card, debit card, or other online payment system"
- Verification through small charge proves adult status

**MFA Method:**
- Suitable for internal operations
- Not approved for third-party sharing without additional verification
- Used as secondary method for enhanced security

### 7.3 Annual Consent Renewal

**COPPA Best Practice:**
- Consent expires annually
- Parent must affirmatively re-consent
- Ensures ongoing awareness and control

**Implementation:**
1. 30 days before expiration: Send renewal reminder
2. 7 days before expiration: Send urgent reminder
3. On expiration: Consent status changes to EXPIRED
4. Data collection stops until renewal
5. Parent can renew anytime via dashboard

**Renewal Process:**
- Same verification method as original consent
- Must review updated privacy policy (if changed)
- New consent record created
- New 365-day expiration date

---

## 8. Appendices

### Appendix A: Parent Communication Templates

**Consent Confirmation Email:**
```
Subject: EduLens - Parental Consent Confirmed

Dear Parent,

Thank you for granting consent for your child to use EduLens.

Consent Details:
- Consent ID: consent_8f7e9d2c
- Date: December 10, 2025 at 2:00 PM
- Expires: December 10, 2026 at 2:00 PM
- Categories: Device Operation, Parental Account

What This Means:
- EduLens can process camera images and voice commands on your device
- All processing happens on your device - nothing is stored or uploaded
- Your account information is stored securely

Your Rights:
- Revoke consent anytime: [Dashboard Link]
- View consent history: [Dashboard Link]
- Download your data: [Dashboard Link]

Questions? Contact us:
- Email: privacy@edulens.com
- Phone: 1-800-EDU-LENS

Best regards,
The EduLens Team
```

### Appendix B: Consent Revocation Workflow

```
Parent Requests Revocation
        ↓
Identity Verification
        ↓
Consent Status → REVOKED
        ↓
Trigger AutoDeletionManager
        ↓
Delete Associated Data
        ↓
Verify Deletion
        ↓
Log Audit Trail
        ↓
Send Confirmation Email
        ↓
Update Parent Dashboard
```

### Appendix C: Compliance Contacts

**Privacy Questions:**
- Email: privacy@edulens.com
- Phone: 1-800-EDU-LENS

**COPPA Compliance:**
- Email: coppa@edulens.com
- Data Protection Officer: dpo@edulens.com

**Legal Department:**
- Email: legal@edulens.com

---

**Document Version:** 1.0
**Last Updated:** December 10, 2025
**Next Review:** March 10, 2026
**Owner:** Security and Privacy Agent (SEC-001)
**Classification:** SECURITY CRITICAL
