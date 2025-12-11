/**
 * DeviceCard component for EduLens Companion App
 * Displays a discovered EduLens device in the scan list
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';

interface DeviceCardProps {
  deviceId: string;
  deviceName: string;
  rssi?: number;
  lastSeen: Date;
  onPress: () => void;
}

export function DeviceCard({
  deviceId,
  deviceName,
  rssi,
  lastSeen,
  onPress,
}: DeviceCardProps): React.JSX.Element {
  const getSignalStrength = (rssi?: number): string => {
    if (!rssi) return 'Unknown';
    if (rssi > -60) return 'Excellent';
    if (rssi > -70) return 'Good';
    if (rssi > -80) return 'Fair';
    return 'Weak';
  };

  const getTimeSinceLastSeen = (date: Date): string => {
    const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);
    if (seconds < 5) return 'Just now';
    if (seconds < 60) return `${seconds}s ago`;
    return `${Math.floor(seconds / 60)}m ago`;
  };

  return (
    <TouchableOpacity style={styles.card} onPress={onPress} activeOpacity={0.7}>
      <View style={styles.deviceIcon}>
        <Text style={styles.iconText}>ED</Text>
      </View>

      <View style={styles.deviceInfo}>
        <Text style={styles.deviceName}>{deviceName}</Text>
        <Text style={styles.deviceId}>ID: {deviceId.substring(0, 8)}...</Text>

        <View style={styles.metaInfo}>
          {rssi && (
            <View style={styles.signalContainer}>
              <View style={[styles.signalDot, { opacity: rssi > -80 ? 1 : 0.3 }]} />
              <View style={[styles.signalDot, { opacity: rssi > -70 ? 1 : 0.3 }]} />
              <View style={[styles.signalDot, { opacity: rssi > -60 ? 1 : 0.3 }]} />
              <Text style={styles.signalText}>{getSignalStrength(rssi)}</Text>
            </View>
          )}
          <Text style={styles.lastSeen}>{getTimeSinceLastSeen(lastSeen)}</Text>
        </View>
      </View>

      <View style={styles.chevron}>
        <Text style={styles.chevronText}>›</Text>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#ffffff',
    padding: 16,
    marginHorizontal: 16,
    marginVertical: 8,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  deviceIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#4A90E2',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  iconText: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: '600',
  },
  deviceInfo: {
    flex: 1,
  },
  deviceName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1A1A1A',
    marginBottom: 4,
  },
  deviceId: {
    fontSize: 12,
    color: '#666666',
    marginBottom: 8,
  },
  metaInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  signalContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
  },
  signalDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#4CAF50',
  },
  signalText: {
    fontSize: 11,
    color: '#666666',
    marginLeft: 4,
  },
  lastSeen: {
    fontSize: 11,
    color: '#999999',
  },
  chevron: {
    marginLeft: 8,
  },
  chevronText: {
    fontSize: 24,
    color: '#CCCCCC',
  },
});
