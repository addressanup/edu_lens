/**
 * DeviceSettingsScreen for EduLens Companion App
 * Configure settings for the connected EduLens device
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  Alert,
} from 'react-native';
import { useBluetooth } from '../../bluetooth/BluetoothContext';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

type DeviceStackParamList = {
  DeviceSettings: { deviceId: string };
  DeviceInfo: { deviceId: string };
};

type Props = NativeStackScreenProps<DeviceStackParamList, 'DeviceSettings'>;

interface DeviceSettings {
  volume: number;
  wakeWordSensitivity: 'low' | 'medium' | 'high';
  displayBrightness: number;
  autoSleep: boolean;
  notificationsEnabled: boolean;
  voiceResponseEnabled: boolean;
  hapticsEnabled: boolean;
}

export function DeviceSettingsScreen({ route, navigation }: Props): React.JSX.Element {
  const { deviceId } = route.params;
  const { sendCommand, connectedDevice } = useBluetooth();

  const [settings, setSettings] = useState<DeviceSettings>({
    volume: 70,
    wakeWordSensitivity: 'medium',
    displayBrightness: 80,
    autoSleep: true,
    notificationsEnabled: true,
    voiceResponseEnabled: true,
    hapticsEnabled: true,
  });

  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    // Load current device settings
    loadDeviceSettings();
  }, []);

  const loadDeviceSettings = async () => {
    // In real implementation, read settings from device
    // For now, using default values
  };

  const updateSetting = async <K extends keyof DeviceSettings>(
    key: K,
    value: DeviceSettings[K]
  ) => {
    setSettings((prev) => ({ ...prev, [key]: value }));

    try {
      // Send command to device
      await sendCommand({
        type: 'SET_VOLUME', // This would be more specific based on the setting
        payload: { [key]: value },
      });
    } catch (error) {
      console.error('Failed to update setting:', error);
      Alert.alert('Error', 'Failed to update device setting');
    }
  };

  const handleVolumeChange = (direction: 'up' | 'down') => {
    const newVolume = direction === 'up'
      ? Math.min(settings.volume + 10, 100)
      : Math.max(settings.volume - 10, 0);
    updateSetting('volume', newVolume);
  };

  const handleBrightnessChange = (direction: 'up' | 'down') => {
    const newBrightness = direction === 'up'
      ? Math.min(settings.displayBrightness + 10, 100)
      : Math.max(settings.displayBrightness - 10, 0);
    updateSetting('displayBrightness', newBrightness);
  };

  const handleSensitivityChange = (value: 'low' | 'medium' | 'high') => {
    updateSetting('wakeWordSensitivity', value);
  };

  const handleFirmwareUpdate = () => {
    Alert.alert(
      'Firmware Update',
      'Check for firmware updates?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Check',
          onPress: () => {
            // In real implementation, check for updates
            Alert.alert('Up to Date', 'Your device is running the latest firmware.');
          },
        },
      ]
    );
  };

  const handleResetDevice = () => {
    Alert.alert(
      'Reset Device',
      'This will reset all device settings to factory defaults. Are you sure?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Reset',
          style: 'destructive',
          onPress: async () => {
            try {
              await sendCommand({ type: 'RESTART' });
              Alert.alert('Success', 'Device has been reset to factory settings.');
            } catch (error) {
              Alert.alert('Error', 'Failed to reset device');
            }
          },
        },
      ]
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Text style={styles.backButton}>‹ Back</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Device Settings</Text>
      </View>

      <ScrollView style={styles.content}>
        {/* Audio Settings */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Audio</Text>

          <View style={styles.settingRow}>
            <Text style={styles.settingLabel}>Volume</Text>
            <View style={styles.sliderControl}>
              <TouchableOpacity
                onPress={() => handleVolumeChange('down')}
                style={styles.sliderButton}
              >
                <Text style={styles.sliderButtonText}>−</Text>
              </TouchableOpacity>
              <View style={styles.sliderValue}>
                <Text style={styles.sliderValueText}>{settings.volume}%</Text>
              </View>
              <TouchableOpacity
                onPress={() => handleVolumeChange('up')}
                style={styles.sliderButton}
              >
                <Text style={styles.sliderButtonText}>+</Text>
              </TouchableOpacity>
            </View>
          </View>

          <View style={styles.settingRow}>
            <Text style={styles.settingLabel}>Voice Responses</Text>
            <Switch
              value={settings.voiceResponseEnabled}
              onValueChange={(value) => updateSetting('voiceResponseEnabled', value)}
              trackColor={{ false: '#D0D0D0', true: '#4A90E2' }}
              thumbColor="#ffffff"
            />
          </View>
        </View>

        {/* Wake Word Settings */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Wake Word</Text>

          <View style={styles.settingColumn}>
            <Text style={styles.settingLabel}>Sensitivity</Text>
            <View style={styles.segmentedControl}>
              <TouchableOpacity
                style={[
                  styles.segment,
                  settings.wakeWordSensitivity === 'low' && styles.segmentActive,
                ]}
                onPress={() => handleSensitivityChange('low')}
              >
                <Text
                  style={[
                    styles.segmentText,
                    settings.wakeWordSensitivity === 'low' && styles.segmentTextActive,
                  ]}
                >
                  Low
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[
                  styles.segment,
                  settings.wakeWordSensitivity === 'medium' && styles.segmentActive,
                ]}
                onPress={() => handleSensitivityChange('medium')}
              >
                <Text
                  style={[
                    styles.segmentText,
                    settings.wakeWordSensitivity === 'medium' && styles.segmentTextActive,
                  ]}
                >
                  Medium
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[
                  styles.segment,
                  settings.wakeWordSensitivity === 'high' && styles.segmentActive,
                ]}
                onPress={() => handleSensitivityChange('high')}
              >
                <Text
                  style={[
                    styles.segmentText,
                    settings.wakeWordSensitivity === 'high' && styles.segmentTextActive,
                  ]}
                >
                  High
                </Text>
              </TouchableOpacity>
            </View>
            <Text style={styles.settingDescription}>
              Higher sensitivity may result in false activations
            </Text>
          </View>
        </View>

        {/* Display Settings */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Display</Text>

          <View style={styles.settingRow}>
            <Text style={styles.settingLabel}>Brightness</Text>
            <View style={styles.sliderControl}>
              <TouchableOpacity
                onPress={() => handleBrightnessChange('down')}
                style={styles.sliderButton}
              >
                <Text style={styles.sliderButtonText}>−</Text>
              </TouchableOpacity>
              <View style={styles.sliderValue}>
                <Text style={styles.sliderValueText}>{settings.displayBrightness}%</Text>
              </View>
              <TouchableOpacity
                onPress={() => handleBrightnessChange('up')}
                style={styles.sliderButton}
              >
                <Text style={styles.sliderButtonText}>+</Text>
              </TouchableOpacity>
            </View>
          </View>

          <View style={styles.settingRow}>
            <Text style={styles.settingLabel}>Auto Sleep</Text>
            <Switch
              value={settings.autoSleep}
              onValueChange={(value) => updateSetting('autoSleep', value)}
              trackColor={{ false: '#D0D0D0', true: '#4A90E2' }}
              thumbColor="#ffffff"
            />
          </View>
        </View>

        {/* Notifications */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Notifications</Text>

          <View style={styles.settingRow}>
            <Text style={styles.settingLabel}>Enable Notifications</Text>
            <Switch
              value={settings.notificationsEnabled}
              onValueChange={(value) => updateSetting('notificationsEnabled', value)}
              trackColor={{ false: '#D0D0D0', true: '#4A90E2' }}
              thumbColor="#ffffff"
            />
          </View>

          <View style={styles.settingRow}>
            <Text style={styles.settingLabel}>Haptic Feedback</Text>
            <Switch
              value={settings.hapticsEnabled}
              onValueChange={(value) => updateSetting('hapticsEnabled', value)}
              trackColor={{ false: '#D0D0D0', true: '#4A90E2' }}
              thumbColor="#ffffff"
            />
          </View>
        </View>

        {/* Device Management */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Device Management</Text>

          <TouchableOpacity
            style={styles.actionButton}
            onPress={handleFirmwareUpdate}
          >
            <Text style={styles.actionButtonText}>Check for Firmware Updates</Text>
            <Text style={styles.chevron}>›</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.actionButton, styles.dangerButton]}
            onPress={handleResetDevice}
          >
            <Text style={[styles.actionButtonText, styles.dangerText]}>
              Reset to Factory Settings
            </Text>
            <Text style={[styles.chevron, styles.dangerText]}>›</Text>
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
  section: {
    backgroundColor: '#ffffff',
    marginHorizontal: 16,
    marginTop: 16,
    padding: 16,
    borderRadius: 12,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1A1A1A',
    marginBottom: 16,
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  settingColumn: {
    paddingVertical: 12,
  },
  settingLabel: {
    fontSize: 14,
    color: '#1A1A1A',
    fontWeight: '500',
  },
  settingDescription: {
    fontSize: 12,
    color: '#999999',
    marginTop: 8,
  },
  sliderControl: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  sliderButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#F0F0F0',
    justifyContent: 'center',
    alignItems: 'center',
  },
  sliderButtonText: {
    fontSize: 20,
    color: '#1A1A1A',
    fontWeight: '600',
  },
  sliderValue: {
    minWidth: 50,
    alignItems: 'center',
  },
  sliderValueText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#4A90E2',
  },
  segmentedControl: {
    flexDirection: 'row',
    backgroundColor: '#F0F0F0',
    borderRadius: 8,
    padding: 2,
    marginTop: 8,
  },
  segment: {
    flex: 1,
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 6,
    alignItems: 'center',
  },
  segmentActive: {
    backgroundColor: '#4A90E2',
  },
  segmentText: {
    fontSize: 14,
    fontWeight: '500',
    color: '#666666',
  },
  segmentTextActive: {
    color: '#ffffff',
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
  dangerButton: {
    borderBottomWidth: 0,
  },
  dangerText: {
    color: '#F44336',
  },
  chevron: {
    fontSize: 20,
    color: '#CCCCCC',
  },
  bottomPadding: {
    height: 40,
  },
});
