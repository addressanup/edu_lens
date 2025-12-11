# EduLens Data Flow Diagram

**Document Version:** 1.0
**Classification:** Internal - Security Critical
**Last Updated:** 2025-12-10
**Owner:** Security and Privacy Team (SEC-001)

---

## 1. Overview

This document describes the complete data flow architecture for the EduLens platform, with explicit privacy annotations at each stage. EduLens is designed with privacy-first principles, particularly for protecting children aged 6-12 in compliance with COPPA and other child protection regulations.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        EDULENS SMART GLASSES                         │
│                         (Edge Device - Layer 1)                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌───────────────┐         ┌─────────────────────────────────┐     │
│  │    Camera     │────────▶│   On-Device Processing Unit     │     │
│  │  (Hardware)   │         │    - Vision Pipeline             │     │
│  │               │         │    - OCR Engine                  │     │
│  │ Privacy LED   │         │    - AI Inference Engine         │     │
│  └───────────────┘         │    - Audio Synthesis             │     │
│                             └──────────┬──────────────────────┘     │
│                                        │                             │
│                                        ▼                             │
│                             ┌─────────────────────────────────┐     │
│                             │   Local Storage (Ephemeral)     │     │
│                             │   - 60-second buffer maximum    │     │
│                             │   - Encrypted at rest           │     │
│                             └──────────┬──────────────────────┘     │
│                                        │                             │
│                                        ▼                             │
│  ┌───────────────┐         ┌─────────────────────────────────┐     │
│  │   Speaker     │◀────────│    Privacy Enforcer Module      │     │
│  │  (Hardware)   │         │  - Data classification check    │     │
│  │               │         │  - Retention policy enforcement │     │
│  └───────────────┘         │  - Anonymization layer          │     │
│                             └──────────┬──────────────────────┘     │
│                                        │                             │
└────────────────────────────────────────┼─────────────────────────────┘
                                         │
                         Encrypted TLS 1.3 Connection
                         (Only for minimal, essential data)
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      CLOUD SERVICES (Layer 2)                        │
│                    [Minimal, COPPA-Compliant]                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Privacy Gateway (Entry Point)                   │   │
│  │  - Consent verification                                      │   │
│  │  - Data classification validation                            │   │
│  │  - Rate limiting per child account                           │   │
│  │  - Audit logging                                             │   │
│  └───────────┬─────────────────────────────────────────────────┘   │
│              │                                                       │
│              ├──────────────────┬──────────────────┐                │
│              ▼                  ▼                  ▼                │
│  ┌─────────────────┐ ┌──────────────────┐ ┌─────────────────────┐ │
│  │  Model Update   │ │  Learning        │ │  Parental Control   │ │
│  │  Service        │ │  Progress        │ │  API                │ │
│  │                 │ │  Aggregation     │ │                     │ │
│  │  - AI model     │ │                  │ │  - Usage reports    │ │
│  │    updates      │ │  - Anonymized    │ │  - Settings sync    │ │
│  │  - Curriculum   │ │    metrics only  │ │  - Consent mgmt     │ │
│  │    content      │ │  - No PII        │ │                     │ │
│  └─────────────────┘ └──────────────────┘ └─────────────────────┘ │
│                                                                       │
└───────────────────────────────────────────┬───────────────────────────┘
                                            │
                         Encrypted Connection (HTTPS)
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PARENTAL COMPANION APP (Layer 3)                  │
│                        (iOS/Android Mobile App)                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Parent Dashboard                                │   │
│  │  - Aggregated learning progress (no detailed content)        │   │
│  │  - Usage time and patterns                                   │   │
│  │  - Subject area breakdown                                    │   │
│  │  - Device settings and controls                              │   │
│  │  - Consent management interface                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Data Flows

### 3.1 Primary Learning Flow (On-Device Only)

**Privacy Level:** MAXIMUM (No external transmission)

```
Step 1: Image Capture
─────────────────────────────────────────────────────
Input:  Child's homework/textbook visible to camera
Process: Camera sensor captures frame
Privacy:
  ✓ Physical LED indicator active when camera is on
  ✓ No facial recognition performed
  ✓ Focus area: documents only (not faces/surroundings)
  ✓ Parent can disable camera via companion app
Data Classification: SENSITIVE_VISUAL
Retention: Immediate processing, no storage
─────────────────────────────────────────────────────

Step 2: Vision Processing
─────────────────────────────────────────────────────
Input:  Raw image frame
Process: OCR extraction, document structure analysis
Privacy:
  ✓ 100% on-device processing (no cloud transmission)
  ✓ Image discarded immediately after text extraction
  ✓ Only text content retained in volatile memory
  ✓ Maximum buffer: 60 seconds
Data Classification: EXTRACTED_TEXT (education content)
Retention: 60-second volatile buffer
Processing Location: Edge device RAM
─────────────────────────────────────────────────────

Step 3: AI Inference
─────────────────────────────────────────────────────
Input:  Extracted text + child's spoken question
Process: Local AI model generates educational response
Privacy:
  ✓ LLM runs entirely on-device
  ✓ No query sent to external servers
  ✓ Voice data processed locally, not stored
  ✓ Conversation context limited to current session
Data Classification: LEARNING_INTERACTION
Retention: Session-only (cleared on device sleep)
Processing Location: Edge device AI accelerator
─────────────────────────────────────────────────────

Step 4: Audio Output
─────────────────────────────────────────────────────
Input:  AI-generated explanation text
Process: Text-to-speech synthesis, audio playback
Privacy:
  ✓ TTS processing on-device
  ✓ No recording of output audio
  ✓ Volume-limited for child safety
Data Classification: AUDIO_OUTPUT
Retention: None (transient audio signal)
Processing Location: Edge device audio processor
─────────────────────────────────────────────────────
```

---

### 3.2 Learning Progress Sync (Cloud - Minimal)

**Privacy Level:** HIGH (Anonymized aggregates only)

```
Step 1: Local Aggregation
─────────────────────────────────────────────────────
Input:  Session metadata from device
Process: Aggregate usage statistics locally
Privacy:
  ✓ NO images or specific homework content
  ✓ NO voice recordings
  ✓ NO personally identifiable information
  ✓ Only: subject area, duration, interaction count
Data Collected:
  - Subject area enum (MATH, READING, SCIENCE, etc.)
  - Session duration (seconds)
  - Number of help requests
  - Timestamp (hour granularity only)
  - Success indicators (binary: helped/not helped)
Data Classification: ANONYMOUS_TELEMETRY
Processing Location: Edge device
─────────────────────────────────────────────────────

Step 2: Consent Check
─────────────────────────────────────────────────────
Input:  Aggregated statistics ready for sync
Process: Verify parental consent for data sharing
Privacy:
  ✓ Check local consent status
  ✓ If consent revoked, data stays on device only
  ✓ If consent expired, prompt parent for renewal
  ✓ Default: NO transmission without active consent
Data Classification: CONSENT_METADATA
Processing Location: Edge device
─────────────────────────────────────────────────────

Step 3: Encrypted Transmission
─────────────────────────────────────────────────────
Input:  Consented, anonymized telemetry
Process: Send to cloud via TLS 1.3 connection
Privacy:
  ✓ TLS 1.3 with certificate pinning
  ✓ Device ID is pseudonymized (rotated quarterly)
  ✓ No IP address logging beyond rate limiting
  ✓ Data minimization: only essential metrics
Transmission Format:
  {
    "device_pseudonym": "hash_abc123",
    "session_date": "2025-12-10",
    "metrics": {
      "math_sessions": 3,
      "reading_sessions": 1,
      "total_duration_minutes": 45
    }
  }
Data Classification: ANONYMOUS_TELEMETRY
Processing Location: Cloud (Privacy Gateway)
─────────────────────────────────────────────────────

Step 4: Cloud Storage (Aggregated Only)
─────────────────────────────────────────────────────
Input:  Anonymized telemetry
Process: Store in time-series database
Privacy:
  ✓ Retention: 90 days maximum
  ✓ Automated purge after retention period
  ✓ No linkage to child's real identity
  ✓ Used only for parental dashboard aggregates
Data Classification: ANONYMOUS_TELEMETRY
Retention: 90 days, then permanent deletion
Processing Location: Cloud (encrypted database)
─────────────────────────────────────────────────────
```

---

### 3.3 Model Update Flow (Cloud to Device)

**Privacy Level:** MEDIUM (Download only, no child data transmitted)

```
Step 1: Update Check
─────────────────────────────────────────────────────
Input:  Current model version on device
Process: Device queries cloud for available updates
Privacy:
  ✓ No child data sent in request
  ✓ Only device model and current version number
  ✓ No user behavior data transmitted
Data Sent: Device model ID, current version number
Data Classification: DEVICE_METADATA
Processing Location: Cloud (Model Update Service)
─────────────────────────────────────────────────────

Step 2: Update Download
─────────────────────────────────────────────────────
Input:  New AI model package
Process: Encrypted download to device
Privacy:
  ✓ Models are general-purpose (not personalized)
  ✓ No child-specific training data in models
  ✓ Parental approval required for updates
Data Classification: SYSTEM_UPDATE
Retention: Persistent (replaces old model)
Processing Location: Edge device storage
─────────────────────────────────────────────────────

Step 3: Curriculum Content Sync
─────────────────────────────────────────────────────
Input:  Updated educational content database
Process: Download age-appropriate content
Privacy:
  ✓ Content is general (not child-specific)
  ✓ Parent can review/approve content categories
  ✓ No tracking of which content is used
Data Classification: EDUCATIONAL_CONTENT
Retention: Persistent until next update
Processing Location: Edge device storage
─────────────────────────────────────────────────────
```

---

### 3.4 Parental Control Flow

**Privacy Level:** HIGH (Parent-controlled, child-protected)

```
Step 1: Consent Management
─────────────────────────────────────────────────────
Input:  Parent action in companion app
Process: Update consent status for child account
Privacy:
  ✓ Parent authenticates with MFA
  ✓ Granular consent controls per data category
  ✓ Consent changes take effect immediately
  ✓ Audit trail of consent changes (parent-viewable)
Consent Categories:
  - Learning progress telemetry (YES/NO)
  - Usage time tracking (YES/NO)
  - Anonymous improvement data (YES/NO)
Data Classification: PARENTAL_CONSENT
Retention: Duration of account + 3 years
Processing Location: Cloud (Parental Control API)
─────────────────────────────────────────────────────

Step 2: Settings Synchronization
─────────────────────────────────────────────────────
Input:  Parent-configured settings
Process: Sync settings to child's device
Privacy:
  ✓ Settings are protective (not invasive)
  ✓ Examples: usage time limits, subject filters
  ✓ No monitoring of specific homework content
  ✓ No live video/audio streaming to parents
Settings Synced:
  - Daily usage time limit
  - Allowed subjects
  - Camera enable/disable
  - Voice interaction enable/disable
Data Classification: DEVICE_SETTINGS
Retention: Active configuration only
Processing Location: Edge device + Cloud sync
─────────────────────────────────────────────────────

Step 3: Progress Dashboard
─────────────────────────────────────────────────────
Input:  Anonymized learning telemetry
Process: Display aggregated insights to parents
Privacy:
  ✓ Aggregated metrics only (no detailed content)
  ✓ Parents see: time spent, subject areas, engagement
  ✓ Parents do NOT see: specific homework, questions asked
  ✓ Designed to inform, not surveil
Dashboard Data:
  - "45 minutes on math this week"
  - "3 reading sessions completed"
  - "Child requested help 12 times"
  - NOT: "Child asked about Pythagorean theorem"
Data Classification: ANONYMOUS_TELEMETRY
Processing Location: Parental Companion App
─────────────────────────────────────────────────────
```

---

## 4. Data Flow Privacy Annotations

### 4.1 Privacy Decision Points

| Decision Point | Privacy Consideration | Implementation |
|----------------|----------------------|----------------|
| Image Capture | Could capture faces or surroundings | Camera angle optimized for documents; physical LED indicator; parent-controlled disable |
| Text Extraction | Homework may contain personal info | OCR limited to educational content; immediate image deletion; no storage of extracted text beyond session |
| Voice Processing | Voice is biometric data | 100% on-device processing; no voice recordings stored; no voice model training |
| AI Inference | Conversation context could be sensitive | Local inference only; session-only context retention; no conversation logging |
| Telemetry Sync | Behavior patterns could identify child | Extreme aggregation; pseudonymized device ID; consent-gated; 90-day retention limit |
| Parental Dashboard | Balance insight vs. surveillance | Show aggregate patterns, hide specific content; empower without invading |

---

### 4.2 Privacy Risk Mitigation

```
RISK: Unauthorized camera activation
MITIGATION:
  → Physical LED indicator (hardware-level, cannot be disabled in software)
  → Parent-controlled camera enable/disable in companion app
  → No remote activation capability
  → Automatic camera shutoff after 10 minutes of inactivity

RISK: Image data leakage
MITIGATION:
  → Images processed in volatile RAM only (never written to persistent storage)
  → Image buffer overwritten immediately after OCR extraction
  → No image data in crash dumps or logs
  → Secure boot ensures no malware can intercept image pipeline

RISK: Voice data collection
MITIGATION:
  → Voice processing 100% on-device (no transmission)
  → No voice recordings stored at any point
  → Voice model runs in isolated secure enclave
  → No voice-based user identification

RISK: Learning content exposure
MITIGATION:
  → Homework content never leaves device
  → AI responses based on on-device models only
  → No logging of questions or answers
  → Session context cleared on device sleep

RISK: Behavioral profiling of children
MITIGATION:
  → Only aggregated, non-identifiable telemetry collected
  → Pseudonymized device IDs rotated quarterly
  → No cross-device tracking
  → No advertising or third-party data sharing (ever)

RISK: Parental over-surveillance
MITIGATION:
  → Parents see aggregate patterns, not specific homework
  → No real-time monitoring features
  → No screen capture or video streaming to parents
  → Dashboard emphasizes support, not surveillance
```

---

## 5. Compliance Mapping

### 5.1 COPPA Requirements

| COPPA Requirement | EduLens Implementation |
|-------------------|------------------------|
| Verifiable parental consent | Multi-factor authentication in companion app; email + SMS verification; explicit consent checkboxes |
| Direct notice to parents | Privacy policy in plain language; in-app notifications of any changes; annual consent renewal |
| Data collection transparency | Clear disclosure of what data is collected (subject, duration, interaction count); what is NOT collected (images, voice, homework content) |
| Parental access rights | Parents can download all collected data via companion app; data provided in machine-readable format |
| Parental deletion rights | Instant deletion of child account and all associated data; automated purge within 24 hours; confirmation email |
| Data security | TLS 1.3 for transmission; AES-256 encryption at rest; secure enclave for sensitive processing |
| Data minimization | Collect only essential telemetry for service improvement; no advertising or third-party sharing |
| Retention limits | 90-day maximum for telemetry; immediate deletion of images; session-only retention of learning context |

---

### 5.2 Additional Privacy Standards

**GDPR-Style Rights (Proactive Compliance):**
- Right to access: Parent dashboard + data export
- Right to erasure: One-click account deletion
- Right to rectification: Parent can correct profile information
- Right to portability: JSON export of all child data
- Right to object: Granular consent controls per data category

**FERPA Considerations (Educational Records):**
- Learning progress data treated as educational records
- No disclosure to third parties without consent
- Parents have access to review and challenge records
- Strict access controls to prevent unauthorized viewing

---

## 6. Data Flow Audit Trail

Every data operation is logged in the audit trail:

```
Example Audit Log Entry:
{
  "timestamp": "2025-12-10T14:23:45Z",
  "operation": "TELEMETRY_SYNC",
  "device_pseudonym": "hash_abc123",
  "data_classification": "ANONYMOUS_TELEMETRY",
  "consent_verified": true,
  "parent_account_id": "parent_xyz789",
  "data_size_bytes": 245,
  "retention_policy": "90_DAYS",
  "processing_location": "CLOUD_US_EAST",
  "compliance_flags": ["COPPA_COMPLIANT", "GDPR_READY"]
}
```

Audit logs are:
- Immutable (append-only)
- Encrypted at rest
- Retained for 7 years (compliance requirement)
- Accessible to parents upon request
- Monitored for anomalies by automated systems

---

## 7. Privacy-First Design Principles

### 7.1 Core Principles

1. **Edge-First Processing:** Maximize on-device computation to minimize data transmission
2. **Data Minimization:** Collect only what's essential; aggregation over raw data
3. **Ephemeral by Default:** Transient data (images, voice) never persisted
4. **Consent-Gated:** No data sharing without explicit, informed parental consent
5. **Transparent Operations:** Parents know exactly what data exists and why
6. **Secure by Design:** Encryption, secure enclaves, regular security audits
7. **Child-Centric:** Every decision prioritizes child safety and privacy

### 7.2 Privacy Guarantees

**We NEVER:**
- Store images of children or their surroundings
- Record or store voice data
- Share data with advertisers or third parties
- Use facial recognition or biometric identification
- Track browsing behavior or online activity
- Sell or monetize child data

**We ALWAYS:**
- Process data on-device when possible
- Encrypt data in transit and at rest
- Obtain verifiable parental consent
- Provide parents with access and deletion rights
- Comply with COPPA and child protection laws
- Design for the child's best interest

---

## 8. Emergency Data Handling

### 8.1 Factory Reset

**Trigger:** Parent initiates factory reset in companion app

**Process:**
1. Device receives authenticated reset command
2. All local storage securely wiped (DoD 5220.22-M standard)
3. Encryption keys destroyed
4. Device returns to out-of-box state
5. Cloud-side child account flagged for deletion
6. All telemetry data purged within 24 hours
7. Parent receives confirmation email

**Data Impact:**
- All on-device data: DELETED
- All cloud telemetry: DELETED
- Parental account: PRESERVED (can set up new child profile)

---

### 8.2 Account Deletion

**Trigger:** Parent deletes child account

**Process:**
1. Parent authenticates with MFA
2. Confirmation dialog explains consequences
3. Grace period: 30 days to change mind
4. After grace period:
   - All child telemetry data: PERMANENTLY DELETED
   - Device deactivated until new account setup
   - Audit logs: RETAINED (compliance requirement, no child PII)
   - Parent notified of completion

**Data Impact:**
- Child-specific data: DELETED
- Compliance logs (anonymized): RETAINED for 7 years
- Device hardware: Can be reassigned to different child

---

## 9. Continuous Privacy Monitoring

### 9.1 Automated Privacy Checks

Daily automated scans verify:
- No images stored on device beyond buffer
- Encryption keys properly rotated
- Consent status synchronized correctly
- Data retention policies enforced
- Audit logs complete and tamper-proof
- No unauthorized data transmission

### 9.2 Privacy Review Schedule

- Weekly: Automated privacy compliance scan
- Monthly: Manual review of data flows by privacy team
- Quarterly: Third-party privacy audit
- Annually: Full privacy impact assessment
- Ad-hoc: Review triggered by any system changes

---

## 10. Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-12-10 | Initial data flow documentation | SEC-001 |

---

**Document Classification:** Internal - Security Critical
**Distribution:** Development Team, Legal, Executive Leadership
**Review Cycle:** Quarterly or upon system changes
