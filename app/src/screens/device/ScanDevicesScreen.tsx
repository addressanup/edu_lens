/**
 * ScanDevicesScreen for EduLens Companion App
 * Allows users to scan for and discover nearby EduLens devices
 */

import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { useBluetooth } from '../../bluetooth/BluetoothContext';
import { DeviceCard } from '../../components/device/DeviceCard';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

type DeviceStackParamList = {
  ScanDevices: undefined;
  Pairing: { deviceId: string; deviceName: string };
  Troubleshooting: undefined;
};

type Props = NativeStackScreenProps<DeviceStackParamList, 'ScanDevices'>;

export function ScanDevicesScreen({ navigation }: Props): React.JSX.Element {
  const {
    isScanning,
    discoveredDevices,
    startScan,
    stopScan,
    error,
    isBluetoothEnabled,
  } = useBluetooth();

  const [scanDuration, setScanDuration] = useState(0);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isScanning) {
      interval = setInterval(() => {
        setScanDuration((prev) => prev + 1);
      }, 1000);
    } else {
      setScanDuration(0);
    }
    return () => clearInterval(interval);
  }, [isScanning]);

  useEffect(() => {
    if (error) {
      Alert.alert('Scan Error', error);
    }
  }, [error]);

  const handleStartScan = async () => {
    if (!isBluetoothEnabled) {
      Alert.alert(
        'Bluetooth Disabled',
        'Please enable Bluetooth to scan for devices.',
        [{ text: 'OK' }]
      );
      return;
    }

    try {
      await startScan();
    } catch (err) {
      console.error('Failed to start scan:', err);
    }
  };

  const handleStopScan = () => {
    stopScan();
  };

  const handleDevicePress = (deviceId: string, deviceName: string) => {
    if (isScanning) {
      stopScan();
    }
    navigation.navigate('Pairing', { deviceId, deviceName });
  };

  const handleTroubleshooting = () => {
    navigation.navigate('Troubleshooting');
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>Find Your EduLens</Text>
        <Text style={styles.subtitle}>
          Make sure your EduLens glasses are powered on and nearby
        </Text>
      </View>

      {/* Scanning Status */}
      {isScanning && (
        <View style={styles.scanningStatus}>
          <ActivityIndicator size="small" color="#4A90E2" />
          <Text style={styles.scanningText}>
            Scanning... ({scanDuration}s)
          </Text>
        </View>
      )}

      {/* Device List */}
      <ScrollView
        style={styles.deviceList}
        contentContainerStyle={styles.deviceListContent}
      >
        {discoveredDevices.length === 0 && !isScanning && (
          <View style={styles.emptyState}>
            <Text style={styles.emptyIcon}>🔍</Text>
            <Text style={styles.emptyTitle}>No Devices Found</Text>
            <Text style={styles.emptySubtitle}>
              Tap "Start Scanning" to search for nearby EduLens devices
            </Text>
          </View>
        )}

        {discoveredDevices.length === 0 && isScanning && (
          <View style={styles.emptyState}>
            <ActivityIndicator size="large" color="#4A90E2" />
            <Text style={styles.emptyTitle}>Searching for devices...</Text>
            <Text style={styles.emptySubtitle}>
              Make sure your EduLens glasses are powered on
            </Text>
          </View>
        )}

        {discoveredDevices.map((device) => (
          <DeviceCard
            key={device.id}
            deviceId={device.id}
            deviceName={device.name}
            lastSeen={device.lastSeen}
            onPress={() => handleDevicePress(device.id, device.name)}
          />
        ))}

        {discoveredDevices.length > 0 && (
          <Text style={styles.deviceCount}>
            {discoveredDevices.length} {discoveredDevices.length === 1 ? 'device' : 'devices'} found
          </Text>
        )}
      </ScrollView>

      {/* Control Buttons */}
      <View style={styles.controls}>
        {!isScanning ? (
          <TouchableOpacity
            style={styles.primaryButton}
            onPress={handleStartScan}
            activeOpacity={0.8}
          >
            <Text style={styles.primaryButtonText}>Start Scanning</Text>
          </TouchableOpacity>
        ) : (
          <TouchableOpacity
            style={[styles.primaryButton, styles.stopButton]}
            onPress={handleStopScan}
            activeOpacity={0.8}
          >
            <Text style={styles.primaryButtonText}>Stop Scanning</Text>
          </TouchableOpacity>
        )}

        <TouchableOpacity
          style={styles.secondaryButton}
          onPress={handleTroubleshooting}
          activeOpacity={0.7}
        >
          <Text style={styles.secondaryButtonText}>Having trouble?</Text>
        </TouchableOpacity>
      </View>

      {/* Bluetooth Status Warning */}
      {!isBluetoothEnabled && (
        <View style={styles.warning}>
          <Text style={styles.warningText}>
            ⚠️ Bluetooth is disabled. Please enable it in Settings.
          </Text>
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
    fontSize: 28,
    fontWeight: '700',
    color: '#1A1A1A',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    color: '#666666',
    lineHeight: 20,
  },
  scanningStatus: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    backgroundColor: '#E3F2FD',
    gap: 12,
  },
  scanningText: {
    fontSize: 14,
    color: '#1976D2',
    fontWeight: '500',
  },
  deviceList: {
    flex: 1,
  },
  deviceListContent: {
    paddingVertical: 16,
    flexGrow: 1,
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 40,
  },
  emptyIcon: {
    fontSize: 64,
    marginBottom: 16,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1A1A1A',
    marginBottom: 8,
    textAlign: 'center',
  },
  emptySubtitle: {
    fontSize: 14,
    color: '#666666',
    textAlign: 'center',
    lineHeight: 20,
  },
  deviceCount: {
    textAlign: 'center',
    fontSize: 12,
    color: '#999999',
    marginTop: 16,
    marginBottom: 8,
  },
  controls: {
    padding: 20,
    backgroundColor: '#ffffff',
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
  },
  primaryButton: {
    backgroundColor: '#4A90E2',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginBottom: 12,
  },
  stopButton: {
    backgroundColor: '#F44336',
  },
  primaryButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
  secondaryButton: {
    padding: 16,
    alignItems: 'center',
  },
  secondaryButtonText: {
    color: '#4A90E2',
    fontSize: 14,
    fontWeight: '500',
  },
  warning: {
    backgroundColor: '#FFF3CD',
    padding: 12,
    margin: 16,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#FFC107',
  },
  warningText: {
    fontSize: 13,
    color: '#856404',
    textAlign: 'center',
  },
});
