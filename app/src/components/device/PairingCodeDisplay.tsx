/**
 * PairingCodeDisplay component for EduLens Companion App
 * Displays a 6-digit pairing code with visual styling
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

interface PairingCodeDisplayProps {
  code: string; // 6-digit code
  title?: string;
  subtitle?: string;
}

export function PairingCodeDisplay({
  code,
  title = 'Pairing Code',
  subtitle = 'Enter this code on your EduLens device',
}: PairingCodeDisplayProps): React.JSX.Element {
  // Ensure code is exactly 6 digits
  const formattedCode = code.padEnd(6, '-').substring(0, 6);
  const digits = formattedCode.split('');

  return (
    <View style={styles.container}>
      {title && <Text style={styles.title}>{title}</Text>}

      <View style={styles.codeContainer}>
        {digits.map((digit, index) => (
          <View key={index} style={styles.digitBox}>
            <Text style={styles.digitText}>{digit}</Text>
          </View>
        ))}
      </View>

      {subtitle && <Text style={styles.subtitle}>{subtitle}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    paddingVertical: 24,
  },
  title: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1A1A1A',
    marginBottom: 20,
  },
  codeContainer: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 16,
  },
  digitBox: {
    width: 48,
    height: 64,
    backgroundColor: '#F5F5F5',
    borderWidth: 2,
    borderColor: '#4A90E2',
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  digitText: {
    fontSize: 32,
    fontWeight: '700',
    color: '#1A1A1A',
    fontVariant: ['tabular-nums'],
  },
  subtitle: {
    fontSize: 14,
    color: '#666666',
    textAlign: 'center',
    marginTop: 8,
  },
});
