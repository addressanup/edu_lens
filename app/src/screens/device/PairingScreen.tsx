/**
 * PairingScreen for EduLens Companion App
 * Handles the Bluetooth pairing process with confirmation code
 */

import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { useBluetooth } from '../../bluetooth/BluetoothContext';
import { PairingCodeDisplay } from '../../components/device/PairingCodeDisplay';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

type DeviceStackParamList = {
  ScanDevices: undefined;
  Pairing: { deviceId: string; deviceName: string };
  DeviceInfo: { deviceId: string };
};

type Props = NativeStackScreenProps<DeviceStackParamList, 'Pairing'>;

type PairingState = 'generating' | 'waiting' | 'pairing' | 'success' | 'failed';

export function PairingScreen({ route, navigation }: Props): React.JSX.Element {
  const { deviceId, deviceName } = route.params;
  const { connectToDevice } = useBluetooth();

  const [pairingState, setPairingState] = useState<PairingState>('generating');
  const [pairingCode, setPairingCode] = useState('');
  const [countdown, setCountdown] = useState(60);
  const [errorMessage, setErrorMessage] = useState('');

  // Generate pairing code
  useEffect(() => {
    const generateCode = () => {
      const code = Math.floor(100000 + Math.random() * 900000).toString();
      setPairingCode(code);
      setPairingState('waiting');
    };

    const timer = setTimeout(generateCode, 1000);
    return () => clearTimeout(timer);
  }, []);

  // Countdown timer
  useEffect(() => {
    if (pairingState === 'waiting' && countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    } else if (countdown === 0) {
      setPairingState('failed');
      setErrorMessage('Pairing code expired. Please try again.');
    }
  }, [pairingState, countdown]);

  // Auto-connect simulation (in real implementation, this would wait for device confirmation)
  useEffect(() => {
    if (pairingState === 'waiting') {
      // Simulate waiting for device to confirm code
      const autoConnect = setTimeout(() => {
        handlePair();
      }, 8000); // Auto-pair after 8 seconds for demo

      return () => clearTimeout(autoConnect);
    }
  }, [pairingState]);

  const handlePair = async () => {
    setPairingState('pairing');
    setErrorMessage('');

    try {
      // In real implementation, verify the pairing code matches on both devices
      await connectToDevice(deviceId);

      setPairingState('success');

      // Navigate to device info after successful pairing
      setTimeout(() => {
        navigation.replace('DeviceInfo', { deviceId });
      }, 2000);
    } catch (error) {
      console.error('Pairing failed:', error);
      setPairingState('failed');
      setErrorMessage('Failed to pair with device. Please try again.');
    }
  };

  const handleCancel = () => {
    Alert.alert(
      'Cancel Pairing',
      'Are you sure you want to cancel pairing?',
      [
        { text: 'No', style: 'cancel' },
        {
          text: 'Yes',
          style: 'destructive',
          onPress: () => navigation.goBack(),
        },
      ]
    );
  };

  const handleRetry = () => {
    setPairingState('generating');
    setCountdown(60);
    setErrorMessage('');
    // Regenerate code
    const code = Math.floor(100000 + Math.random() * 900000).toString();
    setPairingCode(code);
    setPairingState('waiting');
  };

  const renderContent = () => {
    switch (pairingState) {
      case 'generating':
        return (
          <View style={styles.centerContent}>
            <ActivityIndicator size="large" color="#4A90E2" />
            <Text style={styles.statusText}>Generating pairing code...</Text>
          </View>
        );

      case 'waiting':
        return (
          <View style={styles.content}>
            <View style={styles.deviceInfo}>
              <Text style={styles.deviceIcon}>👓</Text>
              <Text style={styles.deviceNameText}>{deviceName}</Text>
            </View>

            <PairingCodeDisplay
              code={pairingCode}
              title="Pairing Code"
              subtitle="Enter this code on your EduLens device"
            />

            <View style={styles.timerContainer}>
              <Text style={styles.timerText}>Code expires in {countdown}s</Text>
            </View>

            <View style={styles.instructions}>
              <Text style={styles.instructionTitle}>Pairing Instructions:</Text>
              <Text style={styles.instructionStep}>1. Look at your EduLens glasses display</Text>
              <Text style={styles.instructionStep}>2. Say "Pair device" or tap the pairing button</Text>
              <Text style={styles.instructionStep}>3. Enter the 6-digit code shown above</Text>
              <Text style={styles.instructionStep}>4. Confirm to complete pairing</Text>
            </View>
          </View>
        );

      case 'pairing':
        return (
          <View style={styles.centerContent}>
            <ActivityIndicator size="large" color="#4A90E2" />
            <Text style={styles.statusText}>Pairing with {deviceName}...</Text>
            <Text style={styles.statusSubtext}>Please wait</Text>
          </View>
        );

      case 'success':
        return (
          <View style={styles.centerContent}>
            <Text style={styles.successIcon}>✓</Text>
            <Text style={styles.successText}>Successfully Paired!</Text>
            <Text style={styles.statusSubtext}>
              Connected to {deviceName}
            </Text>
          </View>
        );

      case 'failed':
        return (
          <View style={styles.centerContent}>
            <Text style={styles.errorIcon}>✕</Text>
            <Text style={styles.errorText}>Pairing Failed</Text>
            <Text style={styles.errorMessage}>{errorMessage}</Text>

            <TouchableOpacity
              style={styles.retryButton}
              onPress={handleRetry}
              activeOpacity={0.8}
            >
              <Text style={styles.retryButtonText}>Try Again</Text>
            </TouchableOpacity>
          </View>
        );
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Pair Device</Text>
      </View>

      <View style={styles.mainContent}>
        {renderContent()}
      </View>

      {(pairingState === 'waiting' || pairingState === 'failed') && (
        <View style={styles.footer}>
          <TouchableOpacity
            style={styles.cancelButton}
            onPress={handleCancel}
            activeOpacity={0.7}
          >
            <Text style={styles.cancelButtonText}>Cancel</Text>
          </TouchableOpacity>
        </View>
      )}
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
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: '#1A1A1A',
  },
  mainContent: {
    flex: 1,
  },
  centerContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 40,
  },
  content: {
    flex: 1,
    padding: 20,
  },
  deviceInfo: {
    alignItems: 'center',
    marginVertical: 24,
  },
  deviceIcon: {
    fontSize: 48,
    marginBottom: 12,
  },
  deviceNameText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1A1A1A',
  },
  timerContainer: {
    alignItems: 'center',
    marginTop: 16,
    marginBottom: 32,
  },
  timerText: {
    fontSize: 14,
    color: '#666666',
    fontWeight: '500',
  },
  instructions: {
    backgroundColor: '#ffffff',
    padding: 20,
    borderRadius: 12,
    marginTop: 20,
  },
  instructionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1A1A1A',
    marginBottom: 12,
  },
  instructionStep: {
    fontSize: 14,
    color: '#666666',
    marginBottom: 8,
    lineHeight: 20,
  },
  statusText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1A1A1A',
    marginTop: 16,
  },
  statusSubtext: {
    fontSize: 14,
    color: '#666666',
    marginTop: 8,
  },
  successIcon: {
    fontSize: 72,
    color: '#4CAF50',
    marginBottom: 16,
  },
  successText: {
    fontSize: 24,
    fontWeight: '700',
    color: '#4CAF50',
    marginBottom: 8,
  },
  errorIcon: {
    fontSize: 72,
    color: '#F44336',
    marginBottom: 16,
  },
  errorText: {
    fontSize: 24,
    fontWeight: '700',
    color: '#F44336',
    marginBottom: 8,
  },
  errorMessage: {
    fontSize: 14,
    color: '#666666',
    textAlign: 'center',
    marginTop: 8,
    marginBottom: 24,
  },
  retryButton: {
    backgroundColor: '#4A90E2',
    paddingHorizontal: 32,
    paddingVertical: 12,
    borderRadius: 8,
    marginTop: 16,
  },
  retryButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
  footer: {
    padding: 20,
    backgroundColor: '#ffffff',
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
  },
  cancelButton: {
    padding: 16,
    alignItems: 'center',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#CCCCCC',
  },
  cancelButtonText: {
    color: '#666666',
    fontSize: 16,
    fontWeight: '500',
  },
});
