/**
 * DeviceInfoScreen for EduLens Companion App
 * Displays information about the connected EduLens device
 */

import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  RefreshControl,
} from 'react-native';
import { useBluetooth } from '../../bluetooth/BluetoothContext';
import { BatteryIndicator } from '../../components/device/BatteryIndicator';
import { ConnectionStatus } from '../../components/device/ConnectionStatus';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

type DeviceStackParamList = {
  DeviceInfo: { deviceId: string };
  DeviceSettings: { deviceId: string };
  ScanDevices: undefined;
};

type Props = NativeStackScreenProps<DeviceStackParamList, 'DeviceInfo'>;

interface DeviceDetails {
  name: string;
  model: string;
  batteryLevel: number;
  isCharging: boolean;
  firmwareVersion: string;
  serialNumber: string;
  lastSync: Date;
  uptime: number;
  wifiConnected: boolean;
}

export function DeviceInfoScreen({ route, navigation }: Props): React.JSX.Element {
  const { deviceId } = route.params;
  const { connectedDevice, disconnectDevice, requestDeviceStatus, requestBatteryLevel } =
    useBluetooth();

  const [deviceDetails, setDeviceDetails] = useState<DeviceDetails>({
    name: 'EduLens Device',
    model: 'EduLens Pro',
    batteryLevel: 0,
    isCharging: false,
    firmwareVersion: '1.0.0',
    serialNumber: 'EL-000000',
    lastSync: new Date(),
    uptime: 0,
    wifiConnected: false,
  });

  const [refreshing, setRefreshing] = useState(false);
  const [isConnected, setIsConnected] = useState(true);

  useEffect(() => {
    loadDeviceInfo();
  }, []);

  const loadDeviceInfo = async () => {
    try {
      const status = await requestDeviceStatus();
      const battery = await requestBatteryLevel();

      setDeviceDetails({
        name: connectedDevice?.name || 'EduLens Device',
        model: 'EduLens Pro',
        batteryLevel: battery,
        isCharging: status.isCharging,
        firmwareVersion: status.firmwareVersion,
        serialNumber: deviceId.substring(0, 10).toUpperCase(),
        lastSync: new Date(),
        uptime: status.uptime,
        wifiConnected: status.wifiConnected,
      });
      setIsConnected(true);
    } catch (error) {
      console.error('Failed to load device info:', error);
      setIsConnected(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadDeviceInfo();
    setRefreshing(false);
  };

  const handleDisconnect = () => {
    Alert.alert(
      'Disconnect Device',
      'Are you sure you want to disconnect from this device?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Disconnect',
          style: 'destructive',
          onPress: async () => {
            await disconnectDevice();
            navigation.replace('ScanDevices');
          },
        },
      ]
    );
  };

  const handleSettings = () => {
    navigation.navigate('DeviceSettings', { deviceId });
  };

  const formatUptime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Device Info</Text>
      </View>

      <ScrollView
        style={styles.content}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
        }
      >
        {/* Device Image/Icon */}
        <View style={styles.deviceImage}>
          <Text style={styles.deviceEmoji}>👓</Text>
        </View>

        {/* Device Name */}
        <Text style={styles.deviceName}>{deviceDetails.name}</Text>
        <Text style={styles.deviceModel}>{deviceDetails.model}</Text>

        {/* Connection Status */}
        <View style={styles.statusContainer}>
          <ConnectionStatus
            status={isConnected ? 'connected' : 'disconnected'}
            size="large"
          />
        </View>

        {/* Battery Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Battery</Text>
            <BatteryIndicator
              level={deviceDetails.batteryLevel}
              isCharging={deviceDetails.isCharging}
              size="medium"
              showPercentage={true}
            />
          </View>
          {deviceDetails.isCharging && (
            <Text style={styles.chargingText}>Charging</Text>
          )}
        </View>

        {/* Device Information */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Device Information</Text>

          <InfoRow label="Firmware Version" value={deviceDetails.firmwareVersion} />
          <InfoRow label="Serial Number" value={deviceDetails.serialNumber} />
          <InfoRow
            label="Last Synced"
            value={deviceDetails.lastSync.toLocaleTimeString()}
          />
          <InfoRow label="Uptime" value={formatUptime(deviceDetails.uptime)} />
        </View>

        {/* Connectivity */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Connectivity</Text>

          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Wi-Fi</Text>
            <View style={styles.infoValueContainer}>
              <View
                style={[
                  styles.statusDot,
                  {
                    backgroundColor: deviceDetails.wifiConnected
                      ? '#4CAF50'
                      : '#9E9E9E',
                  },
                ]}
              />
              <Text style={styles.infoValue}>
                {deviceDetails.wifiConnected ? 'Connected' : 'Disconnected'}
              </Text>
            </View>
          </View>

          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Bluetooth</Text>
            <View style={styles.infoValueContainer}>
              <View
                style={[
                  styles.statusDot,
                  { backgroundColor: isConnected ? '#4CAF50' : '#9E9E9E' },
                ]}
              />
              <Text style={styles.infoValue}>
                {isConnected ? 'Connected' : 'Disconnected'}
              </Text>
            </View>
          </View>
        </View>

        {/* Quick Actions */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Quick Actions</Text>

          <TouchableOpacity
            style={styles.actionButton}
            onPress={handleSettings}
            activeOpacity={0.7}
          >
            <Text style={styles.actionButtonText}>Device Settings</Text>
            <Text style={styles.chevron}>›</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.actionButton}
            onPress={handleRefresh}
            activeOpacity={0.7}
          >
            <Text style={styles.actionButtonText}>Refresh Status</Text>
            <Text style={styles.chevron}>↻</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>

      {/* Disconnect Button */}
      <View style={styles.footer}>
        <TouchableOpacity
          style={styles.disconnectButton}
          onPress={handleDisconnect}
          activeOpacity={0.8}
        >
          <Text style={styles.disconnectButtonText}>Disconnect Device</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
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
  content: {
    flex: 1,
  },
  deviceImage: {
    alignItems: 'center',
    marginVertical: 32,
  },
  deviceEmoji: {
    fontSize: 80,
  },
  deviceName: {
    fontSize: 24,
    fontWeight: '700',
    color: '#1A1A1A',
    textAlign: 'center',
    marginBottom: 4,
  },
  deviceModel: {
    fontSize: 16,
    color: '#666666',
    textAlign: 'center',
    marginBottom: 16,
  },
  statusContainer: {
    alignItems: 'center',
    marginBottom: 24,
  },
  section: {
    backgroundColor: '#ffffff',
    marginHorizontal: 16,
    marginBottom: 16,
    padding: 16,
    borderRadius: 12,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1A1A1A',
    marginBottom: 12,
  },
  chargingText: {
    fontSize: 14,
    color: '#4CAF50',
    fontWeight: '500',
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  infoLabel: {
    fontSize: 14,
    color: '#666666',
  },
  infoValue: {
    fontSize: 14,
    color: '#1A1A1A',
    fontWeight: '500',
  },
  infoValueContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  actionButton: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  actionButtonText: {
    fontSize: 14,
    color: '#4A90E2',
    fontWeight: '500',
  },
  chevron: {
    fontSize: 20,
    color: '#CCCCCC',
  },
  footer: {
    padding: 20,
    backgroundColor: '#ffffff',
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
  },
  disconnectButton: {
    backgroundColor: '#F44336',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  disconnectButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
});
