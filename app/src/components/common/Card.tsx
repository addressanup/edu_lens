/**
 * Common Card Component for EduLens App
 */

import React from 'react';
import {
  View,
  StyleSheet,
  TouchableOpacity,
  ViewStyle,
} from 'react-native';

interface CardProps {
  children: React.ReactNode;
  style?: ViewStyle;
  onPress?: () => void;
  elevated?: boolean;
  padding?: 'none' | 'small' | 'medium' | 'large';
  testID?: string;
}

export const Card: React.FC<CardProps> = ({
  children,
  style,
  onPress,
  elevated = true,
  padding = 'medium',
  testID,
}) => {
  const cardStyles = [
    styles.card,
    elevated && styles.elevated,
    styles[`${padding}Padding`],
    style,
  ];

  if (onPress) {
    return (
      <TouchableOpacity
        style={cardStyles}
        onPress={onPress}
        activeOpacity={0.7}
        testID={testID}
      >
        {children}
      </TouchableOpacity>
    );
  }

  return (
    <View style={cardStyles} testID={testID}>
      {children}
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
  },
  elevated: {
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  nonePadding: {
    padding: 0,
  },
  smallPadding: {
    padding: 12,
  },
  mediumPadding: {
    padding: 16,
  },
  largePadding: {
    padding: 24,
  },
});
