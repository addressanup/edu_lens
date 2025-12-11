/**
 * ConsentForm.tsx
 *
 * COPPA-compliant parental consent form
 * Required before collecting child's personal information
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Linking,
} from 'react-native';

interface ConsentFormProps {
  childName: string;
  onApprove: () => void;
  onDecline: () => void;
}

export function ConsentForm({
  childName,
  onApprove,
  onDecline,
}: ConsentFormProps): React.JSX.Element {
  const [hasRead, setHasRead] = useState(false);
  const [consentsChecked, setConsentsChecked] = useState({
    dataCollection: false,
    voiceRecording: false,
    imageCapture: false,
    dataSharing: false,
  });

  const allConsentsGiven = Object.values(consentsChecked).every((checked) => checked) && hasRead;

  const toggleConsent = (key: keyof typeof consentsChecked): void => {
    setConsentsChecked({
      ...consentsChecked,
      [key]: !consentsChecked[key],
    });
  };

  const openPrivacyPolicy = (): void => {
    // TODO: Replace with actual Privacy Policy URL
    Linking.openURL('https://edulens.com/privacy');
  };

  const openCOPPAInfo = (): void => {
    Linking.openURL('https://www.ftc.gov/legal-library/browse/rules/childrens-online-privacy-protection-rule-coppa');
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerIcon}>🔒</Text>
        <Text style={styles.title}>Parental Consent Required</Text>
        <Text style={styles.subtitle}>
          We need your consent to collect and process information for {childName}'s EduLens experience
        </Text>
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={true}
        onScroll={(event) => {
          const { layoutMeasurement, contentOffset, contentSize } = event.nativeEvent;
          const isCloseToBottom = layoutMeasurement.height + contentOffset.y >= contentSize.height - 20;
          if (isCloseToBottom && !hasRead) {
            setHasRead(true);
          }
        }}
        scrollEventThrottle={400}
      >
        {/* COPPA Information */}
        <View style={styles.coppaSection}>
          <Text style={styles.sectionTitle}>About COPPA Compliance</Text>
          <Text style={styles.bodyText}>
            The Children's Online Privacy Protection Act (COPPA) requires that we obtain
            verifiable parental consent before collecting, using, or disclosing personal
            information from children under 13.
          </Text>
          <TouchableOpacity onPress={openCOPPAInfo} style={styles.linkButton}>
            <Text style={styles.linkText}>Learn more about COPPA →</Text>
          </TouchableOpacity>
        </View>

        {/* What We Collect */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Information We Collect</Text>
          <Text style={styles.bodyText}>
            To provide personalized learning experiences for {childName}, EduLens will collect:
          </Text>

          <View style={styles.listItem}>
            <Text style={styles.bullet}>•</Text>
            <Text style={styles.listText}>
              <Text style={styles.bold}>Profile Information:</Text> Name, age, grade level
            </Text>
          </View>

          <View style={styles.listItem}>
            <Text style={styles.bullet}>•</Text>
            <Text style={styles.listText}>
              <Text style={styles.bold}>Learning Activity:</Text> Questions asked, topics explored,
              learning progress
            </Text>
          </View>

          <View style={styles.listItem}>
            <Text style={styles.bullet}>•</Text>
            <Text style={styles.listText}>
              <Text style={styles.bold}>Voice Recordings:</Text> Audio interactions with the AI
              assistant (processed and not stored permanently)
            </Text>
          </View>

          <View style={styles.listItem}>
            <Text style={styles.bullet}>•</Text>
            <Text style={styles.listText}>
              <Text style={styles.bold}>Image Captures:</Text> Photos of books, worksheets, and
              learning materials (processed for text recognition)
            </Text>
          </View>

          <View style={styles.listItem}>
            <Text style={styles.bullet}>•</Text>
            <Text style={styles.listText}>
              <Text style={styles.bold}>Usage Data:</Text> Device interactions, session duration,
              feature usage
            </Text>
          </View>
        </View>

        {/* How We Use Information */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>How We Use This Information</Text>

          <View style={styles.listItem}>
            <Text style={styles.bullet}>✓</Text>
            <Text style={styles.listText}>
              Provide personalized learning assistance and recommendations
            </Text>
          </View>

          <View style={styles.listItem}>
            <Text style={styles.bullet}>✓</Text>
            <Text style={styles.listText}>
              Track learning progress and generate insights for parents
            </Text>
          </View>

          <View style={styles.listItem}>
            <Text style={styles.bullet}>✓</Text>
            <Text style={styles.listText}>
              Improve the accuracy and effectiveness of our AI models
            </Text>
          </View>

          <View style={styles.listItem}>
            <Text style={styles.bullet}>✓</Text>
            <Text style={styles.listText}>
              Ensure device security and prevent misuse
            </Text>
          </View>
        </View>

        {/* Data Protection */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>How We Protect Your Child's Data</Text>

          <View style={styles.listItem}>
            <Text style={styles.bullet}>🔐</Text>
            <Text style={styles.listText}>
              All data is encrypted in transit and at rest
            </Text>
          </View>

          <View style={styles.listItem}>
            <Text style={styles.bullet}>🔐</Text>
            <Text style={styles.listText}>
              Voice recordings are processed in real-time and not permanently stored
            </Text>
          </View>

          <View style={styles.listItem}>
            <Text style={styles.bullet}>🔐</Text>
            <Text style={styles.listText}>
              We never sell or share your child's information with third parties for marketing
            </Text>
          </View>

          <View style={styles.listItem}>
            <Text style={styles.bullet}>🔐</Text>
            <Text style={styles.listText}>
              You can request to review, delete, or export your child's data at any time
            </Text>
          </View>
        </View>

        {/* Consent Checkboxes */}
        <View style={styles.consentSection}>
          <Text style={styles.sectionTitle}>Your Consent</Text>

          <TouchableOpacity
            style={styles.consentItem}
            onPress={() => toggleConsent('dataCollection')}
          >
            <View style={[styles.checkbox, consentsChecked.dataCollection && styles.checkboxChecked]}>
              {consentsChecked.dataCollection && <Text style={styles.checkmark}>✓</Text>}
            </View>
            <Text style={styles.consentText}>
              I consent to the collection and processing of {childName}'s profile information and
              learning activity data
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.consentItem}
            onPress={() => toggleConsent('voiceRecording')}
          >
            <View style={[styles.checkbox, consentsChecked.voiceRecording && styles.checkboxChecked]}>
              {consentsChecked.voiceRecording && <Text style={styles.checkmark}>✓</Text>}
            </View>
            <Text style={styles.consentText}>
              I consent to voice recordings being processed for AI assistance
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.consentItem}
            onPress={() => toggleConsent('imageCapture')}
          >
            <View style={[styles.checkbox, consentsChecked.imageCapture && styles.checkboxChecked]}>
              {consentsChecked.imageCapture && <Text style={styles.checkmark}>✓</Text>}
            </View>
            <Text style={styles.consentText}>
              I consent to image captures for text recognition and learning assistance
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.consentItem}
            onPress={() => toggleConsent('dataSharing')}
          >
            <View style={[styles.checkbox, consentsChecked.dataSharing && styles.checkboxChecked]}>
              {consentsChecked.dataSharing && <Text style={styles.checkmark}>✓</Text>}
            </View>
            <Text style={styles.consentText}>
              I understand that anonymized usage data may be used to improve EduLens services
            </Text>
          </TouchableOpacity>
        </View>

        {/* Privacy Policy Link */}
        <View style={styles.privacySection}>
          <Text style={styles.privacyText}>
            For more details, please review our{' '}
            <Text style={styles.privacyLink} onPress={openPrivacyPolicy}>
              Privacy Policy
            </Text>
          </Text>
        </View>

        {/* Scroll Indicator */}
        {!hasRead && (
          <View style={styles.scrollIndicator}>
            <Text style={styles.scrollIndicatorText}>↓ Scroll to read all terms ↓</Text>
          </View>
        )}
      </ScrollView>

      {/* Action Buttons */}
      <View style={styles.actions}>
        <TouchableOpacity style={styles.declineButton} onPress={onDecline}>
          <Text style={styles.declineButtonText}>Decline</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.approveButton, !allConsentsGiven && styles.approveButtonDisabled]}
          onPress={onApprove}
          disabled={!allConsentsGiven}
        >
          <Text style={styles.approveButtonText}>I Consent</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  header: {
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingTop: 40,
    paddingBottom: 20,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
  },
  headerIcon: {
    fontSize: 48,
    marginBottom: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1e293b',
    marginBottom: 8,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 14,
    color: '#64748b',
    textAlign: 'center',
    lineHeight: 20,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: 24,
    paddingVertical: 24,
  },
  coppaSection: {
    backgroundColor: '#fef3c7',
    borderLeftWidth: 4,
    borderLeftColor: '#f59e0b',
    borderRadius: 8,
    padding: 16,
    marginBottom: 24,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1e293b',
    marginBottom: 12,
  },
  bodyText: {
    fontSize: 14,
    color: '#334155',
    lineHeight: 22,
    marginBottom: 12,
  },
  bold: {
    fontWeight: '600',
    color: '#1e293b',
  },
  listItem: {
    flexDirection: 'row',
    marginBottom: 12,
    paddingLeft: 8,
  },
  bullet: {
    fontSize: 14,
    color: '#2563eb',
    marginRight: 12,
    fontWeight: 'bold',
  },
  listText: {
    flex: 1,
    fontSize: 14,
    color: '#334155',
    lineHeight: 22,
  },
  linkButton: {
    marginTop: 8,
  },
  linkText: {
    color: '#2563eb',
    fontSize: 14,
    fontWeight: '600',
  },
  consentSection: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  consentItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 16,
  },
  checkbox: {
    width: 24,
    height: 24,
    borderWidth: 2,
    borderColor: '#cbd5e1',
    borderRadius: 4,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
    marginTop: 2,
  },
  checkboxChecked: {
    backgroundColor: '#2563eb',
    borderColor: '#2563eb',
  },
  checkmark: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  consentText: {
    flex: 1,
    fontSize: 14,
    color: '#334155',
    lineHeight: 20,
  },
  privacySection: {
    marginBottom: 24,
  },
  privacyText: {
    fontSize: 13,
    color: '#64748b',
    textAlign: 'center',
    lineHeight: 20,
  },
  privacyLink: {
    color: '#2563eb',
    fontWeight: '600',
    textDecorationLine: 'underline',
  },
  scrollIndicator: {
    backgroundColor: '#eff6ff',
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
  },
  scrollIndicatorText: {
    color: '#2563eb',
    fontSize: 13,
    fontWeight: '600',
    textAlign: 'center',
  },
  actions: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    paddingHorizontal: 24,
    paddingTop: 16,
    paddingBottom: 32,
    borderTopWidth: 1,
    borderTopColor: '#e2e8f0',
    gap: 12,
  },
  declineButton: {
    flex: 1,
    paddingVertical: 14,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#cbd5e1',
    borderRadius: 8,
  },
  declineButtonText: {
    color: '#64748b',
    fontSize: 16,
    fontWeight: '600',
  },
  approveButton: {
    flex: 1,
    backgroundColor: '#2563eb',
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  approveButtonDisabled: {
    backgroundColor: '#94a3b8',
  },
  approveButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
