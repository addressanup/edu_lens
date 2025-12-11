/**
 * TroubleshootingScreen for EduLens Companion App
 * Provides guidance for resolving connection issues
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Linking,
} from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

type DeviceStackParamList = {
  Troubleshooting: undefined;
  ScanDevices: undefined;
};

type Props = NativeStackScreenProps<DeviceStackParamList, 'Troubleshooting'>;

interface TroubleshootingStep {
  id: string;
  title: string;
  description: string;
  expanded: boolean;
}

export function TroubleshootingScreen({ navigation }: Props): React.JSX.Element {
  const [steps, setSteps] = useState<TroubleshootingStep[]>([
    {
      id: '1',
      title: 'Device not appearing in scan',
      description: `• Make sure your EduLens glasses are powered on
• Check that the battery is charged (minimum 20%)
• Ensure Bluetooth is enabled on your phone
• Move closer to the device (within 10 feet)
• Restart both your phone and the glasses
• Check that the glasses are not already paired with another device`,
      expanded: false,
    },
    {
      id: '2',
      title: 'Pairing code not working',
      description: `• Verify you entered the correct 6-digit code
• Check that the code hasn't expired (valid for 60 seconds)
• Make sure both devices are showing the same code
• Try generating a new pairing code
• Restart the pairing process from the beginning`,
      expanded: false,
    },
    {
      id: '3',
      title: 'Connection keeps dropping',
      description: `• Ensure your phone and glasses are within range
• Check for interference from other Bluetooth devices
• Make sure both devices have sufficient battery
• Close other apps that might be using Bluetooth
• Disable and re-enable Bluetooth on your phone
• Forget the device and pair again`,
      expanded: false,
    },
    {
      id: '4',
      title: 'Bluetooth is disabled',
      description: `• Go to your phone's Settings
• Navigate to Bluetooth settings
• Toggle Bluetooth ON
• Return to the EduLens app and try again
• Grant Bluetooth permissions to the app if prompted`,
      expanded: false,
    },
    {
      id: '5',
      title: 'Device shows but won\'t connect',
      description: `• Restart your EduLens glasses
• Clear the Bluetooth cache on your phone:
  - Android: Settings > Apps > Bluetooth > Clear Cache
  - iOS: Toggle Bluetooth off and on in Settings
• Remove any old pairings in your phone's Bluetooth settings
• Try pairing from a different location
• Update the EduLens app to the latest version`,
      expanded: false,
    },
    {
      id: '6',
      title: 'Getting permission errors',
      description: `• Grant location permission (required for Bluetooth on Android)
• Allow Bluetooth permission when prompted
• Check app permissions in Settings:
  - Android: Settings > Apps > EduLens > Permissions
  - iOS: Settings > EduLens > Enable Bluetooth
• Reinstall the app if permissions can't be changed`,
      expanded: false,
    },
  ]);

  const toggleStep = (id: string) => {
    setSteps((prevSteps) =>
      prevSteps.map((step) =>
        step.id === id ? { ...step, expanded: !step.expanded } : step
      )
    );
  };

  const handleContactSupport = () => {
    Linking.openURL('mailto:support@edulens.com?subject=EduLens Connection Help');
  };

  const handleTryAgain = () => {
    navigation.goBack();
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Text style={styles.backButton}>‹ Back</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Troubleshooting</Text>
      </View>

      <ScrollView style={styles.content}>
        <View style={styles.intro}>
          <Text style={styles.introIcon}>🔧</Text>
          <Text style={styles.introTitle}>Connection Issues?</Text>
          <Text style={styles.introText}>
            Try these solutions to resolve common problems with pairing your EduLens device.
          </Text>
        </View>

        {/* Common Issues */}
        <View style={styles.issuesList}>
          {steps.map((step) => (
            <TouchableOpacity
              key={step.id}
              style={styles.issueCard}
              onPress={() => toggleStep(step.id)}
              activeOpacity={0.7}
            >
              <View style={styles.issueHeader}>
                <Text style={styles.issueNumber}>{step.id}</Text>
                <Text style={styles.issueTitle}>{step.title}</Text>
                <Text style={[styles.chevron, step.expanded && styles.chevronExpanded]}>
                  ›
                </Text>
              </View>

              {step.expanded && (
                <View style={styles.issueContent}>
                  <Text style={styles.issueDescription}>{step.description}</Text>
                </View>
              )}
            </TouchableOpacity>
          ))}
        </View>

        {/* Quick Tips */}
        <View style={styles.tipsSection}>
          <Text style={styles.tipsTitle}>Quick Tips</Text>

          <View style={styles.tipCard}>
            <Text style={styles.tipIcon}>💡</Text>
            <View style={styles.tipContent}>
              <Text style={styles.tipTitle}>Keep Devices Close</Text>
              <Text style={styles.tipText}>
                Stay within 10 feet during pairing for best results
              </Text>
            </View>
          </View>

          <View style={styles.tipCard}>
            <Text style={styles.tipIcon}>🔋</Text>
            <View style={styles.tipContent}>
              <Text style={styles.tipTitle}>Check Battery Levels</Text>
              <Text style={styles.tipText}>
                Ensure both devices have at least 20% battery
              </Text>
            </View>
          </View>

          <View style={styles.tipCard}>
            <Text style={styles.tipIcon}>📶</Text>
            <View style={styles.tipContent}>
              <Text style={styles.tipTitle}>Minimize Interference</Text>
              <Text style={styles.tipText}>
                Move away from microwaves, Wi-Fi routers, and other Bluetooth devices
              </Text>
            </View>
          </View>
        </View>

        {/* Still Having Issues */}
        <View style={styles.supportSection}>
          <Text style={styles.supportTitle}>Still Having Issues?</Text>
          <Text style={styles.supportText}>
            If you've tried these solutions and still can't connect, our support team is here to
            help.
          </Text>

          <TouchableOpacity
            style={styles.supportButton}
            onPress={handleContactSupport}
            activeOpacity={0.8}
          >
            <Text style={styles.supportButtonText}>Contact Support</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.secondaryButton}
            onPress={handleTryAgain}
            activeOpacity={0.7}
          >
            <Text style={styles.secondaryButtonText}>Try Scanning Again</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.bottomPadding} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F8F9FA',
  },
  header: {
    padding: 20,
    paddingTop: 60,
    backgroundColor: '#ffffff',
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  backButton: {
    fontSize: 18,
    color: '#4A90E2',
    marginBottom: 8,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: '#1A1A1A',
  },
  content: {
    flex: 1,
  },
  intro: {
    alignItems: 'center',
    padding: 24,
    backgroundColor: '#ffffff',
    marginBottom: 16,
  },
  introIcon: {
    fontSize: 48,
    marginBottom: 12,
  },
  introTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#1A1A1A',
    marginBottom: 8,
  },
  introText: {
    fontSize: 14,
    color: '#666666',
    textAlign: 'center',
    lineHeight: 20,
  },
  issuesList: {
    marginHorizontal: 16,
  },
  issueCard: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    marginBottom: 12,
    overflow: 'hidden',
  },
  issueHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
  },
  issueNumber: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#4A90E2',
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '700',
    textAlign: 'center',
    lineHeight: 28,
    marginRight: 12,
  },
  issueTitle: {
    flex: 1,
    fontSize: 15,
    fontWeight: '600',
    color: '#1A1A1A',
  },
  chevron: {
    fontSize: 24,
    color: '#CCCCCC',
    transform: [{ rotate: '0deg' }],
  },
  chevronExpanded: {
    transform: [{ rotate: '90deg' }],
  },
  issueContent: {
    paddingHorizontal: 16,
    paddingBottom: 16,
    paddingLeft: 56,
  },
  issueDescription: {
    fontSize: 14,
    color: '#666666',
    lineHeight: 22,
  },
  tipsSection: {
    margin: 16,
    padding: 16,
    backgroundColor: '#ffffff',
    borderRadius: 12,
  },
  tipsTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1A1A1A',
    marginBottom: 16,
  },
  tipCard: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 16,
  },
  tipIcon: {
    fontSize: 24,
    marginRight: 12,
  },
  tipContent: {
    flex: 1,
  },
  tipTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1A1A1A',
    marginBottom: 4,
  },
  tipText: {
    fontSize: 13,
    color: '#666666',
    lineHeight: 18,
  },
  supportSection: {
    margin: 16,
    padding: 20,
    backgroundColor: '#ffffff',
    borderRadius: 12,
    alignItems: 'center',
  },
  supportTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1A1A1A',
    marginBottom: 8,
  },
  supportText: {
    fontSize: 14,
    color: '#666666',
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 20,
  },
  supportButton: {
    backgroundColor: '#4A90E2',
    paddingHorizontal: 32,
    paddingVertical: 14,
    borderRadius: 12,
    width: '100%',
    alignItems: 'center',
    marginBottom: 12,
  },
  supportButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
  secondaryButton: {
    paddingHorizontal: 32,
    paddingVertical: 14,
    borderRadius: 12,
    width: '100%',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#4A90E2',
  },
  secondaryButtonText: {
    color: '#4A90E2',
    fontSize: 16,
    fontWeight: '600',
  },
  bottomPadding: {
    height: 40,
  },
});
