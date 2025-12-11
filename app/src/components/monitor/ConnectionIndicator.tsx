/**
 * ConnectionIndicator Component
 *
 * Shows the WebSocket connection status.
 */

import React from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { ConnectionStatus } from '../../services/realtimeStream';
import { colors } from '../../theme/colors';
import { spacing } from '../../theme/spacing';

interface ConnectionIndicatorProps {
  status: ConnectionStatus;
}

const getStatusColor = (status: ConnectionStatus): string => {
  switch (status) {
    case 'connected':
      return colors.success;
    case 'connecting':
    case 'reconnecting':
      return colors.warning;
    case 'error':
      return colors.error;
    default:
      return colors.textSecondary;
  }
};

const getStatusLabel = (status: ConnectionStatus): string => {
  switch (status) {
    case 'connected':
      return 'LIVE';
    case 'connecting':
      return 'Connecting...';
    case 'reconnecting':
      return 'Reconnecting...';
    case 'error':
      return 'Error';
    default:
      return 'Disconnected';
  }
};

const ConnectionIndicator: React.FC<ConnectionIndicatorProps> = ({ status }) => {
  const color = getStatusColor(status);
  const label = getStatusLabel(status);
  const isLoading = status === 'connecting' || status === 'reconnecting';

  return (
    <View style={[styles.container, { backgroundColor: `${color}20` }]}>
      {isLoading ? (
        <ActivityIndicator size="small" color={color} style={styles.indicator} />
      ) : (
        <View style={[styles.dot, { backgroundColor: color }]} />
      )}
      <Text style={[styles.label, { color }]}>{label}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    borderRadius: 12,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: spacing.xs,
  },
  indicator: {
    marginRight: spacing.xs,
  },
  label: {
    fontSize: 12,
    fontWeight: '600',
  },
});

export default ConnectionIndicator;
