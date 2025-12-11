/**
 * SocialLoginButtons.tsx
 *
 * Reusable social login button component
 * Supports Google and Apple authentication
 */

import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Platform,
} from 'react-native';

interface SocialLoginButtonsProps {
  onGooglePress: () => void;
  onApplePress: () => void;
  disabled?: boolean;
}

export function SocialLoginButtons({
  onGooglePress,
  onApplePress,
  disabled = false,
}: SocialLoginButtonsProps): React.JSX.Element {
  return (
    <View style={styles.container}>
      {/* Google Login Button */}
      <TouchableOpacity
        style={[styles.socialButton, styles.googleButton, disabled && styles.buttonDisabled]}
        onPress={onGooglePress}
        disabled={disabled}
      >
        <View style={styles.buttonContent}>
          <Text style={styles.googleIcon}>G</Text>
          <Text style={styles.googleButtonText}>Continue with Google</Text>
        </View>
      </TouchableOpacity>

      {/* Apple Login Button - iOS only */}
      {Platform.OS === 'ios' && (
        <TouchableOpacity
          style={[styles.socialButton, styles.appleButton, disabled && styles.buttonDisabled]}
          onPress={onApplePress}
          disabled={disabled}
        >
          <View style={styles.buttonContent}>
            <Text style={styles.appleIcon}></Text>
            <Text style={styles.appleButtonText}>Continue with Apple</Text>
          </View>
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    width: '100%',
    gap: 12,
  },
  socialButton: {
    borderRadius: 8,
    paddingVertical: 12,
    paddingHorizontal: 16,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
    minHeight: 48,
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  buttonContent: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  googleButton: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#cbd5e1',
  },
  googleIcon: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#4285f4',
    marginRight: 12,
    width: 24,
    textAlign: 'center',
  },
  googleButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1e293b',
  },
  appleButton: {
    backgroundColor: '#000',
  },
  appleIcon: {
    fontSize: 20,
    color: '#fff',
    marginRight: 12,
    width: 24,
    textAlign: 'center',
  },
  appleButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
});
