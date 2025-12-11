/**
 * TimeSlider Component
 * Slider for setting time limits with formatted display
 */

import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ViewStyle,
} from 'react-native';
import Slider from '@react-native-community/slider';

interface TimeSliderProps {
  label: string;
  value: number; // in minutes
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
  style?: ViewStyle;
  showTime?: boolean;
}

export const TimeSlider: React.FC<TimeSliderProps> = ({
  label,
  value,
  onChange,
  min = 0,
  max = 240, // 4 hours
  step = 15,
  disabled = false,
  style,
  showTime = true,
}) => {
  const formatTime = (minutes: number): string => {
    if (minutes === 0) return 'No limit';
    if (minutes < 60) return `${minutes} min`;

    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;

    if (mins === 0) return `${hours} hr`;
    return `${hours} hr ${mins} min`;
  };

  return (
    <View style={[styles.container, style]}>
      <View style={styles.header}>
        <Text style={styles.label}>{label}</Text>
        {showTime && (
          <Text style={styles.value}>{formatTime(value)}</Text>
        )}
      </View>

      <Slider
        style={styles.slider}
        minimumValue={min}
        maximumValue={max}
        step={step}
        value={value}
        onValueChange={onChange}
        minimumTrackTintColor="#4A90A4"
        maximumTrackTintColor="#E8F4F8"
        thumbTintColor="#4A90A4"
        disabled={disabled}
      />

      <View style={styles.minMax}>
        <Text style={styles.minMaxText}>{formatTime(min)}</Text>
        <Text style={styles.minMaxText}>{formatTime(max)}</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    paddingVertical: 12,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  label: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333333',
  },
  value: {
    fontSize: 16,
    fontWeight: '700',
    color: '#4A90A4',
  },
  slider: {
    width: '100%',
    height: 40,
  },
  minMax: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 4,
  },
  minMaxText: {
    fontSize: 12,
    color: '#999999',
  },
});
