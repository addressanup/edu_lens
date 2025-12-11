/**
 * ForgotPasswordScreen.tsx
 *
 * Password reset screen for parents who forgot their credentials
 * Features:
 * - Email-based password reset
 * - Email validation
 * - Success feedback
 * - Navigation back to login
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { useAuth } from '../../auth/AuthContext';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

type Props = NativeStackScreenProps<any, 'ForgotPassword'>;

export function ForgotPasswordScreen({ navigation }: Props): React.JSX.Element {
  const { resetPassword } = useAuth();
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const handleResetPassword = async (): Promise<void> => {
    // Clear previous errors
    setError(null);

    // Validate email
    if (!email.trim()) {
      setError('Email is required');
      return;
    }

    if (!validateEmail(email)) {
      setError('Please enter a valid email address');
      return;
    }

    setIsLoading(true);
    try {
      await resetPassword(email.trim().toLowerCase());
      setEmailSent(true);
    } catch (err) {
      Alert.alert(
        'Reset Failed',
        'Unable to send password reset email. Please verify your email address and try again.',
        [{ text: 'OK' }]
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleBackToLogin = (): void => {
    navigation.navigate('Login');
  };

  const handleResendEmail = async (): Promise<void> => {
    setEmailSent(false);
    await handleResetPassword();
  };

  if (emailSent) {
    return (
      <View style={styles.container}>
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <View style={styles.successContainer}>
            <View style={styles.iconContainer}>
              <Text style={styles.iconText}>✉️</Text>
            </View>

            <Text style={styles.successTitle}>Check Your Email</Text>

            <Text style={styles.successMessage}>
              We've sent password reset instructions to:
            </Text>

            <Text style={styles.emailText}>{email}</Text>

            <Text style={styles.instructionText}>
              Please check your inbox and follow the link to reset your password. The link will
              expire in 24 hours.
            </Text>

            <View style={styles.infoBox}>
              <Text style={styles.infoText}>
                Didn't receive the email? Check your spam folder or try resending.
              </Text>
            </View>

            <TouchableOpacity
              style={styles.primaryButton}
              onPress={handleBackToLogin}
            >
              <Text style={styles.primaryButtonText}>Back to Login</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.secondaryButton}
              onPress={handleResendEmail}
            >
              <Text style={styles.secondaryButtonText}>Resend Email</Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 64 : 0}
    >
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.header}>
          <View style={styles.iconContainer}>
            <Text style={styles.iconText}>🔐</Text>
          </View>

          <Text style={styles.title}>Forgot Password?</Text>
          <Text style={styles.subtitle}>
            No worries! Enter your email address and we'll send you instructions to reset your
            password.
          </Text>
        </View>

        <View style={styles.form}>
          {/* Email Input */}
          <View style={styles.inputGroup}>
            <Text style={styles.label}>Email Address</Text>
            <TextInput
              style={[styles.input, error ? styles.inputError : null]}
              placeholder="parent@example.com"
              placeholderTextColor="#999"
              value={email}
              onChangeText={(text) => {
                setEmail(text);
                if (error) setError(null);
              }}
              keyboardType="email-address"
              autoCapitalize="none"
              autoComplete="email"
              autoCorrect={false}
              autoFocus
              editable={!isLoading}
            />
            {error && <Text style={styles.errorText}>{error}</Text>}
          </View>

          {/* Reset Button */}
          <TouchableOpacity
            style={[styles.resetButton, isLoading && styles.resetButtonDisabled]}
            onPress={handleResetPassword}
            disabled={isLoading}
          >
            {isLoading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.resetButtonText}>Send Reset Instructions</Text>
            )}
          </TouchableOpacity>

          {/* Back to Login */}
          <TouchableOpacity
            style={styles.backButton}
            onPress={handleBackToLogin}
            disabled={isLoading}
          >
            <Text style={styles.backButtonText}>← Back to Login</Text>
          </TouchableOpacity>
        </View>

        {/* Security Note */}
        <View style={styles.securityNote}>
          <Text style={styles.securityText}>
            For your security, password reset links expire after 24 hours. If you don't receive
            an email within a few minutes, please check your spam folder.
          </Text>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  scrollContent: {
    flexGrow: 1,
    paddingHorizontal: 24,
    paddingVertical: 32,
    justifyContent: 'center',
  },
  header: {
    alignItems: 'center',
    marginBottom: 40,
  },
  iconContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#eff6ff',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 24,
  },
  iconText: {
    fontSize: 40,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#1e293b',
    marginBottom: 12,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 16,
    color: '#64748b',
    textAlign: 'center',
    lineHeight: 24,
  },
  form: {
    width: '100%',
    marginBottom: 24,
  },
  inputGroup: {
    marginBottom: 24,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#334155',
    marginBottom: 8,
  },
  input: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#cbd5e1',
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 16,
    color: '#1e293b',
  },
  inputError: {
    borderColor: '#ef4444',
  },
  errorText: {
    color: '#ef4444',
    fontSize: 12,
    marginTop: 4,
  },
  resetButton: {
    backgroundColor: '#2563eb',
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
    minHeight: 48,
  },
  resetButtonDisabled: {
    backgroundColor: '#94a3b8',
  },
  resetButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  backButton: {
    alignItems: 'center',
    paddingVertical: 12,
  },
  backButtonText: {
    color: '#2563eb',
    fontSize: 16,
    fontWeight: '600',
  },
  securityNote: {
    backgroundColor: '#f1f5f9',
    borderRadius: 8,
    padding: 16,
    marginTop: 'auto',
  },
  securityText: {
    color: '#475569',
    fontSize: 12,
    lineHeight: 18,
    textAlign: 'center',
  },
  // Success Screen Styles
  successContainer: {
    alignItems: 'center',
    paddingVertical: 20,
  },
  successTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#1e293b',
    marginBottom: 16,
    textAlign: 'center',
  },
  successMessage: {
    fontSize: 16,
    color: '#64748b',
    textAlign: 'center',
    marginBottom: 12,
  },
  emailText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2563eb',
    marginBottom: 24,
    textAlign: 'center',
  },
  instructionText: {
    fontSize: 14,
    color: '#64748b',
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 24,
    paddingHorizontal: 20,
  },
  infoBox: {
    backgroundColor: '#fef3c7',
    borderLeftWidth: 4,
    borderLeftColor: '#f59e0b',
    borderRadius: 8,
    padding: 16,
    marginBottom: 32,
  },
  infoText: {
    color: '#92400e',
    fontSize: 14,
    lineHeight: 20,
  },
  primaryButton: {
    backgroundColor: '#2563eb',
    borderRadius: 8,
    paddingVertical: 14,
    paddingHorizontal: 32,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
    width: '100%',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  primaryButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  secondaryButton: {
    paddingVertical: 12,
    paddingHorizontal: 32,
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
  },
  secondaryButtonText: {
    color: '#2563eb',
    fontSize: 16,
    fontWeight: '600',
  },
});
