/**
 * BatteryIndicator component for EduLens Companion App
 * Displays battery level with visual representation
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

interface BatteryIndicatorProps {
  level: number; // 0-100
  isCharging?: boolean;
  size?: 'small' | 'medium' | 'large';
  showPercentage?: boolean;
}

export function BatteryIndicator({
  level,
  isCharging = false,
  size = 'medium',
  showPercentage = true,
}: BatteryIndicatorProps): React.JSX.Element {
  const getBatteryColor = (level: number): string => {
    if (level > 50) return '#4CAF50';
    if (level > 20) return '#FFA726';
    return '#F44336';
  };

  const getBatteryWidth = (): number => {
    switch (size) {
      case 'small':
        return 32;
      case 'large':
        return 48;
      default:
        return 40;
    }
  };

  const getBatteryHeight = (): number => {
    switch (size) {
      case 'small':
        return 16;
      case 'large':
        return 24;
      default:
        return 20;
    }
  };

  const getFontSize = (): number => {
    switch (size) {
      case 'small':
        return 10;
      case 'large':
        return 14;
      default:
        return 12;
    }
  };

  const width = getBatteryWidth();
  const height = getBatteryHeight();
  const color = getBatteryColor(level);
  const fillWidth = Math.max(2, (width - 4) * (level / 100));

  return (
    <View style={styles.container}>
      <View style={styles.batteryContainer}>
        {/* Battery body */}
        <View style={[styles.battery, { width, height, borderColor: color }]}>
          <View
            style={[
              styles.batteryFill,
              {
                width: fillWidth,
                backgroundColor: color,
              },
            ]}
          />
        </View>

        {/* Battery tip */}
        <View
          style={[
            styles.batteryTip,
            {
              height: height * 0.4,
              backgroundColor: color,
            },
          ]}
        />

        {/* Charging indicator */}
        {isCharging && (
          <View style={styles.chargingIndicator}>
            <Text style={[styles.chargingIcon, { fontSize: height * 0.6 }]}>⚡</Text>
          </View>
        )}
      </View>

      {/* Percentage text */}
      {showPercentage && (
        <Text style={[styles.percentageText, { fontSize: getFontSize(), color }]}>
          {level}%
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  batteryContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    position: 'relative',
  },
  battery: {
    borderWidth: 2,
    borderRadius: 3,
    padding: 2,
    justifyContent: 'center',
  },
  batteryFill: {
    height: '100%',
    borderRadius: 1,
  },
  batteryTip: {
    width: 3,
    borderTopRightRadius: 2,
    borderBottomRightRadius: 2,
    marginLeft: -1,
  },
  chargingIndicator: {
    position: 'absolute',
    left: 0,
    right: 0,
    top: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
  },
  chargingIcon: {
    color: '#ffffff',
    fontWeight: 'bold',
  },
  percentageText: {
    fontWeight: '600',
  },
});
