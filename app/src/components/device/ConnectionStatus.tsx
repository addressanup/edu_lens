/**
 * ConnectionStatus component for EduLens Companion App
 * Displays the current connection status with the device
 */

import React from 'react';
import { View, Text, StyleSheet, Animated } from 'react-native';

type ConnectionState = 'connected' | 'connecting' | 'disconnected' | 'error';

interface ConnectionStatusProps {
  status: ConnectionState;
  showLabel?: boolean;
  size?: 'small' | 'medium' | 'large';
}

export function ConnectionStatus({
  status,
  showLabel = true,
  size = 'medium',
}: ConnectionStatusProps): React.JSX.Element {
  const pulseAnim = React.useRef(new Animated.Value(1)).current;

  React.useEffect(() => {
    if (status === 'connecting') {
      const pulse = Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, {
            toValue: 1.3,
            duration: 800,
            useNativeDriver: true,
          }),
          Animated.timing(pulseAnim, {
            toValue: 1,
            duration: 800,
            useNativeDriver: true,
          }),
        ])
      );
      pulse.start();
      return () => pulse.stop();
    } else {
      pulseAnim.setValue(1);
    }
  }, [status, pulseAnim]);

  const getStatusConfig = (state: ConnectionState) => {
    switch (state) {
      case 'connected':
        return {
          color: '#4CAF50',
          label: 'Connected',
          icon: '●',
        };
      case 'connecting':
        return {
          color: '#FFA726',
          label: 'Connecting...',
          icon: '◐',
        };
      case 'error':
        return {
          color: '#F44336',
          label: 'Connection Error',
          icon: '●',
        };
      default:
        return {
          color: '#9E9E9E',
          label: 'Disconnected',
          icon: '○',
        };
    }
  };

  const getDotSize = (): number => {
    switch (size) {
      case 'small':
        return 8;
      case 'large':
        return 16;
      default:
        return 12;
    }
  };

  const getFontSize = (): number => {
    switch (size) {
      case 'small':
        return 11;
      case 'large':
        return 15;
      default:
        return 13;
    }
  };

  const config = getStatusConfig(status);
  const dotSize = getDotSize();

  return (
    <View style={styles.container}>
      <Animated.View
        style={[
          styles.statusDot,
          {
            width: dotSize,
            height: dotSize,
            backgroundColor: config.color,
            transform: status === 'connecting' ? [{ scale: pulseAnim }] : [],
          },
        ]}
      />
      {showLabel && (
        <Text style={[styles.statusLabel, { fontSize: getFontSize(), color: config.color }]}>
          {config.label}
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  statusDot: {
    borderRadius: 100,
  },
  statusLabel: {
    fontWeight: '500',
  },
});
