/**
 * SetupDeviceScreen.tsx
 *
 * Screen for setting up and pairing EduLens device
 * Provides instructions and initiates Bluetooth pairing process
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { OnboardingProgress } from '../../components/onboarding/OnboardingProgress';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

type Props = NativeStackScreenProps<any, 'SetupDevice'>;

export function SetupDeviceScreen({ navigation }: Props): React.JSX.Element {
  const [isScanning, setIsScanning] = useState(false);
  const [isPairing, setIsPairing] = useState(false);

  const handleStartPairing = async (): Promise<void> => {
    setIsScanning(true);
    try {
      // TODO: Implement actual Bluetooth scanning and pairing
      // This will integrate with the BluetoothContext
      await new Promise((resolve) => setTimeout(resolve, 2000));

      Alert.alert(
        'Pairing',
        'Bluetooth pairing will be implemented. For now, you can continue with the onboarding.',
        [
          {
            text: 'Skip for Now',
            onPress: handleSkipSetup,
          },
          {
            text: 'Continue',
            onPress: handleSkipSetup,
          },
        ]
      );
    } catch (error) {
      Alert.alert(
        'Pairing Failed',
        'Unable to find EduLens device. Please make sure the device is turned on and nearby.',
        [{ text: 'Try Again' }]
      );
    } finally {
      setIsScanning(false);
    }
  };

  const handleSkipSetup = (): void => {
    Alert.alert(
      'Skip Device Setup?',
      'You can set up your EduLens device later from Settings. Would you like to continue?',
      [
        {
          text: 'Cancel',
          style: 'cancel',
        },
        {
          text: 'Skip',
          onPress: () => navigation.navigate('OnboardingComplete'),
        },
      ]
    );
  };

  return (
    <View style={styles.container}>
      <OnboardingProgress currentStep={3} totalSteps={3} />

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.content}>
          {/* Header */}
          <View style={styles.header}>
            <View style={styles.iconContainer}>
              <Text style={styles.iconText}>👓</Text>
            </View>
            <Text style={styles.title}>Set Up Your Device</Text>
            <Text style={styles.subtitle}>
              Let's connect your EduLens glasses to complete the setup
            </Text>
          </View>

          {/* Setup Instructions */}
          <View style={styles.instructionsSection}>
            <Text style={styles.sectionTitle}>Before You Begin</Text>

            <View style={styles.instructionCard}>
              <View style={styles.instructionStep}>
                <View style={styles.stepBadge}>
                  <Text style={styles.stepBadgeText}>1</Text>
                </View>
                <View style={styles.stepContent}>
                  <Text style={styles.stepTitle}>Charge Your Device</Text>
                  <Text style={styles.stepDescription}>
                    Make sure your EduLens glasses are charged and powered on
                  </Text>
                </View>
              </View>

              <View style={styles.instructionStep}>
                <View style={styles.stepBadge}>
                  <Text style={styles.stepBadgeText}>2</Text>
                </View>
                <View style={styles.stepContent}>
                  <Text style={styles.stepTitle}>Enable Bluetooth</Text>
                  <Text style={styles.stepDescription}>
                    Ensure Bluetooth is enabled on your phone
                  </Text>
                </View>
              </View>

              <View style={styles.instructionStep}>
                <View style={styles.stepBadge}>
                  <Text style={styles.stepBadgeText}>3</Text>
                </View>
                <View style={styles.stepContent}>
                  <Text style={styles.stepTitle}>Keep Device Nearby</Text>
                  <Text style={styles.stepDescription}>
                    Place your EduLens glasses within 10 feet of your phone
                  </Text>
                </View>
              </View>

              <View style={styles.instructionStep}>
                <View style={styles.stepBadge}>
                  <Text style={styles.stepBadgeText}>4</Text>
                </View>
                <View style={styles.stepContent}>
                  <Text style={styles.stepTitle}>Enter Pairing Mode</Text>
                  <Text style={styles.stepDescription}>
                    Press and hold the power button for 3 seconds until the LED blinks blue
                  </Text>
                </View>
              </View>
            </View>
          </View>

          {/* Device Features Preview */}
          <View style={styles.featuresSection}>
            <Text style={styles.sectionTitle}>What You'll Be Able to Do</Text>

            <View style={styles.featuresList}>
              <View style={styles.featureItem}>
                <Text style={styles.featureIcon}>✓</Text>
                <Text style={styles.featureText}>Control device settings remotely</Text>
              </View>

              <View style={styles.featureItem}>
                <Text style={styles.featureIcon}>✓</Text>
                <Text style={styles.featureText}>Monitor battery level and status</Text>
              </View>

              <View style={styles.featureItem}>
                <Text style={styles.featureIcon}>✓</Text>
                <Text style={styles.featureText}>Update parental controls in real-time</Text>
              </View>

              <View style={styles.featureItem}>
                <Text style={styles.featureIcon}>✓</Text>
                <Text style={styles.featureText}>Sync learning progress and activity</Text>
              </View>
            </View>
          </View>

          {/* Troubleshooting Tip */}
          <View style={styles.tipBox}>
            <Text style={styles.tipIcon}>💡</Text>
            <View style={styles.tipContent}>
              <Text style={styles.tipTitle}>Troubleshooting Tip</Text>
              <Text style={styles.tipText}>
                If you're having trouble pairing, try restarting both your phone and the EduLens
                device, then try again.
              </Text>
            </View>
          </View>
        </View>
      </ScrollView>

      {/* Bottom Actions */}
      <View style={styles.bottomActions}>
        <TouchableOpacity
          style={styles.skipButton}
          onPress={handleSkipSetup}
          disabled={isScanning || isPairing}
        >
          <Text style={styles.skipButtonText}>Skip for Now</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[
            styles.pairButton,
            (isScanning || isPairing) && styles.pairButtonDisabled,
          ]}
          onPress={handleStartPairing}
          disabled={isScanning || isPairing}
        >
          {isScanning || isPairing ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <>
              <Text style={styles.pairButtonText}>Start Pairing</Text>
              <Text style={styles.pairButtonIcon}>→</Text>
            </>
          )}
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
  scrollContent: {
    flexGrow: 1,
    paddingHorizontal: 24,
    paddingTop: 20,
    paddingBottom: 120,
  },
  content: {
    width: '100%',
  },
  header: {
    alignItems: 'center',
    marginBottom: 40,
  },
  iconContainer: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: '#eff6ff',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 24,
    shadowColor: '#2563eb',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 5,
  },
  iconText: {
    fontSize: 48,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#1e293b',
    marginBottom: 8,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 16,
    color: '#64748b',
    textAlign: 'center',
    lineHeight: 24,
  },
  instructionsSection: {
    marginBottom: 32,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#1e293b',
    marginBottom: 16,
  },
  instructionCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  instructionStep: {
    flexDirection: 'row',
    marginBottom: 20,
  },
  stepBadge: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#2563eb',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 16,
  },
  stepBadgeText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },
  stepContent: {
    flex: 1,
  },
  stepTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1e293b',
    marginBottom: 4,
  },
  stepDescription: {
    fontSize: 14,
    color: '#64748b',
    lineHeight: 20,
  },
  featuresSection: {
    marginBottom: 24,
  },
  featuresList: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  featureItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  featureIcon: {
    fontSize: 20,
    color: '#10b981',
    marginRight: 12,
    fontWeight: 'bold',
  },
  featureText: {
    flex: 1,
    fontSize: 15,
    color: '#334155',
    lineHeight: 22,
  },
  tipBox: {
    flexDirection: 'row',
    backgroundColor: '#fef3c7',
    borderLeftWidth: 4,
    borderLeftColor: '#f59e0b',
    borderRadius: 8,
    padding: 16,
    marginBottom: 20,
  },
  tipIcon: {
    fontSize: 24,
    marginRight: 12,
  },
  tipContent: {
    flex: 1,
  },
  tipTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: '#92400e',
    marginBottom: 4,
  },
  tipText: {
    fontSize: 13,
    color: '#92400e',
    lineHeight: 20,
  },
  bottomActions: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    backgroundColor: '#fff',
    paddingHorizontal: 24,
    paddingTop: 16,
    paddingBottom: 32,
    borderTopWidth: 1,
    borderTopColor: '#e2e8f0',
    gap: 12,
  },
  skipButton: {
    flex: 1,
    paddingVertical: 14,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#cbd5e1',
    borderRadius: 8,
  },
  skipButtonText: {
    color: '#64748b',
    fontSize: 16,
    fontWeight: '600',
  },
  pairButton: {
    flex: 2,
    backgroundColor: '#2563eb',
    borderRadius: 8,
    paddingVertical: 14,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 48,
    shadowColor: '#2563eb',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 4,
  },
  pairButtonDisabled: {
    backgroundColor: '#94a3b8',
  },
  pairButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    marginRight: 8,
  },
  pairButtonIcon: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
});
