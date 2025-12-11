/**
 * SafetySettingsScreen
 * Screen for managing safety and privacy settings
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  SafeAreaView,
  TouchableOpacity,
  Alert,
  TextInput,
  Modal,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { SafetyToggle, SafetySetting } from '../../components/controls/SafetyToggle';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';

const SAFETY_SETTINGS: SafetySetting[] = [
  {
    id: 'voice_recording',
    title: 'Voice Recording',
    description: 'Allow device to record voice for tutoring interactions',
    enabled: true,
    level: 'important',
    icon: '🎤',
  },
  {
    id: 'camera_access',
    title: 'Camera Access',
    description: 'Enable camera for OCR text scanning features',
    enabled: true,
    level: 'important',
    icon: '📷',
  },
  {
    id: 'location_tracking',
    title: 'Location Services',
    description: 'Track device location for safety and security',
    enabled: false,
    level: 'optional',
    icon: '📍',
  },
  {
    id: 'data_collection',
    title: 'Learning Analytics',
    description: 'Collect usage data to improve learning recommendations',
    enabled: true,
    level: 'optional',
    icon: '📊',
  },
];

const PRIVACY_SETTINGS: SafetySetting[] = [
  {
    id: 'share_progress',
    title: 'Share Progress Reports',
    description: 'Share anonymized learning data to improve EduLens',
    enabled: false,
    level: 'optional',
    icon: '📈',
  },
  {
    id: 'third_party_sharing',
    title: 'Third-Party Sharing',
    description: 'Allow sharing data with educational partners',
    enabled: false,
    level: 'optional',
    icon: '🔗',
    locked: true,
  },
  {
    id: 'cloud_backup',
    title: 'Cloud Backup',
    description: 'Automatically backup learning data to cloud',
    enabled: true,
    level: 'important',
    icon: '☁️',
  },
];

const SECURITY_SETTINGS: SafetySetting[] = [
  {
    id: 'biometric_auth',
    title: 'Biometric Authentication',
    description: 'Use fingerprint or face ID to unlock app',
    enabled: false,
    level: 'important',
    icon: '🔐',
  },
  {
    id: 'pin_required',
    title: 'PIN Protection',
    description: 'Require PIN to access parental controls',
    enabled: true,
    level: 'critical',
    icon: '🔢',
  },
  {
    id: 'auto_lock',
    title: 'Auto-Lock App',
    description: 'Automatically lock app after inactivity',
    enabled: true,
    level: 'important',
    icon: '🔒',
  },
];

export const SafetySettingsScreen: React.FC = () => {
  const navigation = useNavigation();

  const [safetySettings, setSafetySettings] = useState<SafetySetting[]>(SAFETY_SETTINGS);
  const [privacySettings, setPrivacySettings] = useState<SafetySetting[]>(PRIVACY_SETTINGS);
  const [securitySettings, setSecuritySettings] = useState<SafetySetting[]>(SECURITY_SETTINGS);
  const [emergencyContact, setEmergencyContact] = useState({
    name: '',
    phone: '',
    email: '',
  });
  const [showPinModal, setShowPinModal] = useState(false);
  const [pin, setPin] = useState('');
  const [hasChanges, setHasChanges] = useState(false);

  const handleSafetyToggle = (settingId: string, enabled: boolean) => {
    setSafetySettings((prev) =>
      prev.map((setting) =>
        setting.id === settingId ? { ...setting, enabled } : setting
      )
    );
    setHasChanges(true);
  };

  const handlePrivacyToggle = (settingId: string, enabled: boolean) => {
    setPrivacySettings((prev) =>
      prev.map((setting) =>
        setting.id === settingId ? { ...setting, enabled } : setting
      )
    );
    setHasChanges(true);
  };

  const handleSecurityToggle = (settingId: string, enabled: boolean) => {
    if (settingId === 'pin_required' && enabled) {
      setShowPinModal(true);
    }

    setSecuritySettings((prev) =>
      prev.map((setting) =>
        setting.id === settingId ? { ...setting, enabled } : setting
      )
    );
    setHasChanges(true);
  };

  const handleSavePin = () => {
    if (pin.length !== 4) {
      Alert.alert('Invalid PIN', 'PIN must be 4 digits');
      return;
    }

    Alert.alert('Success', 'PIN set successfully');
    setShowPinModal(false);
    setPin('');
  };

  const handleEmergencyContactSave = () => {
    if (!emergencyContact.name || !emergencyContact.phone) {
      Alert.alert('Error', 'Please provide at least name and phone number');
      return;
    }

    Alert.alert('Success', 'Emergency contact saved');
    setHasChanges(false);
  };

  const handleSave = async () => {
    Alert.alert('Success', 'Safety settings updated successfully');
    setHasChanges(false);
  };

  const handleExportData = () => {
    Alert.alert(
      'Export Data',
      'Export all learning data and settings?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Export',
          onPress: () => {
            Alert.alert('Success', 'Data export will be sent to your email');
          },
        },
      ]
    );
  };

  const handleDeleteData = () => {
    Alert.alert(
      'Delete All Data',
      'This will permanently delete all learning data. This action cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: () => {
            Alert.alert('Deleted', 'All data has been deleted');
          },
        },
      ]
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.scrollView} contentContainerStyle={styles.content}>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity
            onPress={() => navigation.goBack()}
            style={styles.backButton}
          >
            <Text style={styles.backText}>‹ Back</Text>
          </TouchableOpacity>
          <Text style={styles.title}>Safety & Privacy</Text>
          <Text style={styles.subtitle}>
            Manage security and privacy settings
          </Text>
        </View>

        {/* Safety Settings */}
        <Card style={styles.card}>
          <Text style={styles.cardTitle}>Safety Settings</Text>
          <Text style={styles.cardDescription}>
            Control device permissions and features
          </Text>

          <View style={styles.settingsList}>
            {safetySettings.map((setting) => (
              <SafetyToggle
                key={setting.id}
                setting={setting}
                onToggle={handleSafetyToggle}
              />
            ))}
          </View>
        </Card>

        {/* Privacy Settings */}
        <Card style={styles.card}>
          <Text style={styles.cardTitle}>Privacy Settings</Text>
          <Text style={styles.cardDescription}>
            Manage data collection and sharing
          </Text>

          <View style={styles.settingsList}>
            {privacySettings.map((setting) => (
              <SafetyToggle
                key={setting.id}
                setting={setting}
                onToggle={handlePrivacyToggle}
              />
            ))}
          </View>

          <View style={styles.privacyNote}>
            <Text style={styles.privacyNoteText}>
              🔒 We never sell your data. Read our{' '}
              <Text style={styles.link}>Privacy Policy</Text> for more details.
            </Text>
          </View>
        </Card>

        {/* Security Settings */}
        <Card style={styles.card}>
          <Text style={styles.cardTitle}>Security Settings</Text>
          <Text style={styles.cardDescription}>
            Protect your account and app access
          </Text>

          <View style={styles.settingsList}>
            {securitySettings.map((setting) => (
              <SafetyToggle
                key={setting.id}
                setting={setting}
                onToggle={handleSecurityToggle}
              />
            ))}
          </View>
        </Card>

        {/* Emergency Contact */}
        <Card style={styles.card}>
          <Text style={styles.cardTitle}>Emergency Contact</Text>
          <Text style={styles.cardDescription}>
            Contact to reach in case of emergency
          </Text>

          <View style={styles.emergencyForm}>
            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Name</Text>
              <TextInput
                style={styles.input}
                placeholder="Emergency contact name"
                value={emergencyContact.name}
                onChangeText={(text) => {
                  setEmergencyContact((prev) => ({ ...prev, name: text }));
                  setHasChanges(true);
                }}
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Phone Number</Text>
              <TextInput
                style={styles.input}
                placeholder="(555) 123-4567"
                value={emergencyContact.phone}
                onChangeText={(text) => {
                  setEmergencyContact((prev) => ({ ...prev, phone: text }));
                  setHasChanges(true);
                }}
                keyboardType="phone-pad"
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Email (Optional)</Text>
              <TextInput
                style={styles.input}
                placeholder="emergency@example.com"
                value={emergencyContact.email}
                onChangeText={(text) => {
                  setEmergencyContact((prev) => ({ ...prev, email: text }));
                  setHasChanges(true);
                }}
                keyboardType="email-address"
              />
            </View>

            <Button
              title="Save Emergency Contact"
              onPress={handleEmergencyContactSave}
              variant="outline"
              style={styles.emergencyButton}
            />
          </View>
        </Card>

        {/* Data Management */}
        <Card style={styles.card}>
          <Text style={styles.cardTitle}>Data Management</Text>
          <Text style={styles.cardDescription}>
            Manage your stored data
          </Text>

          <View style={styles.dataActions}>
            <TouchableOpacity
              style={styles.dataActionButton}
              onPress={handleExportData}
            >
              <Text style={styles.dataActionIcon}>📥</Text>
              <View style={styles.dataActionInfo}>
                <Text style={styles.dataActionTitle}>Export Data</Text>
                <Text style={styles.dataActionDescription}>
                  Download all learning data
                </Text>
              </View>
            </TouchableOpacity>

            <View style={styles.divider} />

            <TouchableOpacity
              style={styles.dataActionButton}
              onPress={handleDeleteData}
            >
              <Text style={styles.dataActionIcon}>🗑️</Text>
              <View style={styles.dataActionInfo}>
                <Text style={[styles.dataActionTitle, styles.dangerText]}>
                  Delete All Data
                </Text>
                <Text style={styles.dataActionDescription}>
                  Permanently remove all data
                </Text>
              </View>
            </TouchableOpacity>
          </View>
        </Card>

        {/* Actions */}
        <View style={styles.actions}>
          <Button
            title="Save Changes"
            onPress={handleSave}
            disabled={!hasChanges}
            style={styles.saveButton}
          />
        </View>

        <View style={styles.bottomPadding} />
      </ScrollView>

      {/* PIN Modal */}
      <Modal
        visible={showPinModal}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setShowPinModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Set PIN</Text>
            <Text style={styles.modalDescription}>
              Enter a 4-digit PIN to protect parental controls
            </Text>

            <TextInput
              style={styles.pinInput}
              placeholder="Enter 4-digit PIN"
              value={pin}
              onChangeText={setPin}
              keyboardType="number-pad"
              maxLength={4}
              secureTextEntry
            />

            <View style={styles.modalActions}>
              <Button
                title="Cancel"
                onPress={() => {
                  setShowPinModal(false);
                  setPin('');
                }}
                variant="outline"
                style={styles.modalButton}
              />
              <Button
                title="Set PIN"
                onPress={handleSavePin}
                style={styles.modalButton}
              />
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F8FAFB',
  },
  scrollView: {
    flex: 1,
  },
  content: {
    padding: 20,
  },
  header: {
    marginBottom: 24,
  },
  backButton: {
    marginBottom: 12,
  },
  backText: {
    fontSize: 16,
    color: '#4A90A4',
    fontWeight: '600',
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: '#333333',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#666666',
  },
  card: {
    marginBottom: 16,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#333333',
    marginBottom: 6,
  },
  cardDescription: {
    fontSize: 14,
    color: '#666666',
    marginBottom: 16,
  },
  settingsList: {
    gap: 8,
  },
  privacyNote: {
    backgroundColor: '#E8F4F8',
    padding: 12,
    borderRadius: 8,
    marginTop: 16,
  },
  privacyNoteText: {
    fontSize: 14,
    color: '#4A90A4',
    lineHeight: 20,
  },
  link: {
    fontWeight: '600',
    textDecorationLine: 'underline',
  },
  emergencyForm: {
    gap: 16,
  },
  inputGroup: {
    gap: 8,
  },
  inputLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333333',
  },
  input: {
    backgroundColor: '#F8FAFB',
    borderWidth: 1,
    borderColor: '#E0E0E0',
    borderRadius: 12,
    padding: 14,
    fontSize: 16,
    color: '#333333',
  },
  emergencyButton: {
    marginTop: 8,
  },
  dataActions: {
    gap: 16,
  },
  dataActionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    backgroundColor: '#F8FAFB',
    borderRadius: 12,
  },
  dataActionIcon: {
    fontSize: 32,
    marginRight: 16,
  },
  dataActionInfo: {
    flex: 1,
  },
  dataActionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333333',
    marginBottom: 4,
  },
  dataActionDescription: {
    fontSize: 14,
    color: '#999999',
  },
  dangerText: {
    color: '#FF5252',
  },
  divider: {
    height: 1,
    backgroundColor: '#F0F0F0',
  },
  actions: {
    marginTop: 24,
  },
  saveButton: {
    width: '100%',
  },
  bottomPadding: {
    height: 40,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalContent: {
    backgroundColor: '#FFFFFF',
    borderRadius: 24,
    padding: 24,
    width: '100%',
    maxWidth: 400,
  },
  modalTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#333333',
    marginBottom: 8,
  },
  modalDescription: {
    fontSize: 16,
    color: '#666666',
    marginBottom: 24,
  },
  pinInput: {
    backgroundColor: '#F8FAFB',
    borderWidth: 1,
    borderColor: '#E0E0E0',
    borderRadius: 12,
    padding: 16,
    fontSize: 24,
    textAlign: 'center',
    letterSpacing: 8,
    marginBottom: 24,
  },
  modalActions: {
    flexDirection: 'row',
    gap: 12,
  },
  modalButton: {
    flex: 1,
  },
});
