/**
 * SignUpScreen.tsx
 *
 * Registration screen for new parents with COPPA compliance
 * Features:
 * - Email/password registration
 * - Age verification (must be 18+)
 * - Terms of Service and Privacy Policy acceptance
 * - Input validation and password strength checking
 * - COPPA compliance requirements
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
  Linking,
} from 'react-native';
import { useAuth } from '../../auth/AuthContext';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

type Props = NativeStackScreenProps<any, 'SignUp'>;

interface FormErrors {
  name?: string;
  email?: string;
  password?: string;
  confirmPassword?: string;
  birthYear?: string;
  terms?: string;
}

export function SignUpScreen({ navigation }: Props): React.JSX.Element {
  const { register } = useAuth();
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    birthYear: '',
  });
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<FormErrors>({});
  const [passwordStrength, setPasswordStrength] = useState<'weak' | 'medium' | 'strong' | null>(null);

  const currentYear = new Date().getFullYear();
  const minYear = currentYear - 100;
  const maxYear = currentYear - 18; // Must be 18+ for COPPA compliance

  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const checkPasswordStrength = (password: string): 'weak' | 'medium' | 'strong' => {
    let strength = 0;
    if (password.length >= 8) strength++;
    if (password.length >= 12) strength++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
    if (/\d/.test(password)) strength++;
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) strength++;

    if (strength <= 2) return 'weak';
    if (strength <= 4) return 'medium';
    return 'strong';
  };

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    // Name validation
    if (!formData.name.trim()) {
      newErrors.name = 'Full name is required';
    } else if (formData.name.trim().length < 2) {
      newErrors.name = 'Name must be at least 2 characters';
    }

    // Email validation
    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!validateEmail(formData.email)) {
      newErrors.email = 'Please enter a valid email address';
    }

    // Password validation
    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters';
    } else if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(formData.password)) {
      newErrors.password = 'Password must contain uppercase, lowercase, and numbers';
    }

    // Confirm password validation
    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Please confirm your password';
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    // Age verification (COPPA compliance - must be 18+)
    const birthYear = parseInt(formData.birthYear);
    if (!formData.birthYear) {
      newErrors.birthYear = 'Birth year is required for age verification';
    } else if (isNaN(birthYear) || birthYear < minYear || birthYear > maxYear) {
      newErrors.birthYear = `You must be 18 or older to register (born in ${maxYear} or earlier)`;
    }

    // Terms acceptance
    if (!termsAccepted) {
      newErrors.terms = 'You must accept the Terms of Service and Privacy Policy';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleRegister = async (): Promise<void> => {
    if (!validateForm()) {
      return;
    }

    setIsLoading(true);
    try {
      await register(
        formData.email.trim().toLowerCase(),
        formData.password,
        formData.name.trim()
      );

      // Navigate to onboarding
      navigation.reset({
        index: 0,
        routes: [{ name: 'Onboarding' }],
      });
    } catch (error) {
      Alert.alert(
        'Registration Failed',
        error instanceof Error ? error.message : 'Unable to create account. Please try again.',
        [{ text: 'OK' }]
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogin = (): void => {
    navigation.navigate('Login');
  };

  const openTermsOfService = (): void => {
    // TODO: Replace with actual Terms of Service URL
    Linking.openURL('https://edulens.com/terms');
  };

  const openPrivacyPolicy = (): void => {
    // TODO: Replace with actual Privacy Policy URL
    Linking.openURL('https://edulens.com/privacy');
  };

  const updateFormField = (field: keyof typeof formData, value: string): void => {
    setFormData({ ...formData, [field]: value });

    // Clear error for this field
    if (errors[field as keyof FormErrors]) {
      setErrors({ ...errors, [field]: undefined });
    }

    // Update password strength indicator
    if (field === 'password' && value) {
      setPasswordStrength(checkPasswordStrength(value));
    } else if (field === 'password' && !value) {
      setPasswordStrength(null);
    }
  };

  const getPasswordStrengthColor = (): string => {
    switch (passwordStrength) {
      case 'weak': return '#ef4444';
      case 'medium': return '#f59e0b';
      case 'strong': return '#10b981';
      default: return '#cbd5e1';
    }
  };

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
          <Text style={styles.logo}>EduLens</Text>
          <Text style={styles.subtitle}>Create Your Parent Account</Text>
        </View>

        <View style={styles.form}>
          {/* Full Name Input */}
          <View style={styles.inputGroup}>
            <Text style={styles.label}>Full Name</Text>
            <TextInput
              style={[styles.input, errors.name ? styles.inputError : null]}
              placeholder="John Doe"
              placeholderTextColor="#999"
              value={formData.name}
              onChangeText={(text) => updateFormField('name', text)}
              autoComplete="name"
              autoCapitalize="words"
              editable={!isLoading}
            />
            {errors.name && <Text style={styles.errorText}>{errors.name}</Text>}
          </View>

          {/* Email Input */}
          <View style={styles.inputGroup}>
            <Text style={styles.label}>Email Address</Text>
            <TextInput
              style={[styles.input, errors.email ? styles.inputError : null]}
              placeholder="parent@example.com"
              placeholderTextColor="#999"
              value={formData.email}
              onChangeText={(text) => updateFormField('email', text)}
              keyboardType="email-address"
              autoCapitalize="none"
              autoComplete="email"
              autoCorrect={false}
              editable={!isLoading}
            />
            {errors.email && <Text style={styles.errorText}>{errors.email}</Text>}
          </View>

          {/* Birth Year Input (Age Verification for COPPA) */}
          <View style={styles.inputGroup}>
            <Text style={styles.label}>Birth Year (Age Verification)</Text>
            <TextInput
              style={[styles.input, errors.birthYear ? styles.inputError : null]}
              placeholder={`e.g., ${maxYear - 30}`}
              placeholderTextColor="#999"
              value={formData.birthYear}
              onChangeText={(text) => updateFormField('birthYear', text.replace(/[^0-9]/g, ''))}
              keyboardType="number-pad"
              maxLength={4}
              editable={!isLoading}
            />
            <Text style={styles.helperText}>
              You must be 18 or older to use EduLens (COPPA requirement)
            </Text>
            {errors.birthYear && <Text style={styles.errorText}>{errors.birthYear}</Text>}
          </View>

          {/* Password Input */}
          <View style={styles.inputGroup}>
            <Text style={styles.label}>Password</Text>
            <TextInput
              style={[styles.input, errors.password ? styles.inputError : null]}
              placeholder="Enter a strong password"
              placeholderTextColor="#999"
              value={formData.password}
              onChangeText={(text) => updateFormField('password', text)}
              secureTextEntry
              autoCapitalize="none"
              autoComplete="password-new"
              editable={!isLoading}
            />
            {passwordStrength && (
              <View style={styles.passwordStrengthContainer}>
                <View style={styles.passwordStrengthBar}>
                  <View
                    style={[
                      styles.passwordStrengthFill,
                      {
                        width: passwordStrength === 'weak' ? '33%' : passwordStrength === 'medium' ? '66%' : '100%',
                        backgroundColor: getPasswordStrengthColor(),
                      },
                    ]}
                  />
                </View>
                <Text style={[styles.passwordStrengthText, { color: getPasswordStrengthColor() }]}>
                  {passwordStrength.charAt(0).toUpperCase() + passwordStrength.slice(1)}
                </Text>
              </View>
            )}
            {errors.password && <Text style={styles.errorText}>{errors.password}</Text>}
          </View>

          {/* Confirm Password Input */}
          <View style={styles.inputGroup}>
            <Text style={styles.label}>Confirm Password</Text>
            <TextInput
              style={[styles.input, errors.confirmPassword ? styles.inputError : null]}
              placeholder="Re-enter your password"
              placeholderTextColor="#999"
              value={formData.confirmPassword}
              onChangeText={(text) => updateFormField('confirmPassword', text)}
              secureTextEntry
              autoCapitalize="none"
              autoComplete="password-new"
              editable={!isLoading}
            />
            {errors.confirmPassword && <Text style={styles.errorText}>{errors.confirmPassword}</Text>}
          </View>

          {/* Terms and Privacy Policy Acceptance */}
          <View style={styles.checkboxContainer}>
            <TouchableOpacity
              style={styles.checkbox}
              onPress={() => {
                setTermsAccepted(!termsAccepted);
                if (errors.terms) {
                  setErrors({ ...errors, terms: undefined });
                }
              }}
              disabled={isLoading}
            >
              <View style={[styles.checkboxBox, termsAccepted && styles.checkboxBoxChecked]}>
                {termsAccepted && <Text style={styles.checkboxCheck}>✓</Text>}
              </View>
            </TouchableOpacity>
            <View style={styles.checkboxTextContainer}>
              <Text style={styles.checkboxText}>
                I accept the{' '}
                <Text style={styles.link} onPress={openTermsOfService}>
                  Terms of Service
                </Text>
                {' '}and{' '}
                <Text style={styles.link} onPress={openPrivacyPolicy}>
                  Privacy Policy
                </Text>
              </Text>
            </View>
          </View>
          {errors.terms && <Text style={styles.errorText}>{errors.terms}</Text>}

          {/* Sign Up Button */}
          <TouchableOpacity
            style={[styles.signUpButton, isLoading && styles.signUpButtonDisabled]}
            onPress={handleRegister}
            disabled={isLoading}
          >
            {isLoading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.signUpButtonText}>Create Account</Text>
            )}
          </TouchableOpacity>

          {/* Login Link */}
          <View style={styles.loginContainer}>
            <Text style={styles.loginText}>Already have an account? </Text>
            <TouchableOpacity onPress={handleLogin} disabled={isLoading}>
              <Text style={styles.loginLink}>Sign In</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* COPPA Compliance Notice */}
        <View style={styles.coppaNotice}>
          <Text style={styles.coppaText}>
            EduLens is committed to protecting children's privacy in compliance with the Children's
            Online Privacy Protection Act (COPPA). You must be 18 or older to create an account and
            provide parental consent for your child's use of EduLens.
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
  },
  header: {
    alignItems: 'center',
    marginBottom: 32,
    marginTop: 20,
  },
  logo: {
    fontSize: 36,
    fontWeight: 'bold',
    color: '#2563eb',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 18,
    color: '#334155',
    textAlign: 'center',
  },
  form: {
    width: '100%',
    marginBottom: 24,
  },
  inputGroup: {
    marginBottom: 20,
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
  helperText: {
    color: '#64748b',
    fontSize: 12,
    marginTop: 4,
  },
  passwordStrengthContainer: {
    marginTop: 8,
  },
  passwordStrengthBar: {
    height: 4,
    backgroundColor: '#e2e8f0',
    borderRadius: 2,
    overflow: 'hidden',
    marginBottom: 4,
  },
  passwordStrengthFill: {
    height: '100%',
    borderRadius: 2,
  },
  passwordStrengthText: {
    fontSize: 12,
    fontWeight: '600',
  },
  checkboxContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 24,
    marginTop: 8,
  },
  checkbox: {
    marginRight: 12,
  },
  checkboxBox: {
    width: 24,
    height: 24,
    borderWidth: 2,
    borderColor: '#cbd5e1',
    borderRadius: 4,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#fff',
  },
  checkboxBoxChecked: {
    backgroundColor: '#2563eb',
    borderColor: '#2563eb',
  },
  checkboxCheck: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  checkboxTextContainer: {
    flex: 1,
  },
  checkboxText: {
    fontSize: 14,
    color: '#334155',
    lineHeight: 20,
  },
  link: {
    color: '#2563eb',
    fontWeight: '600',
    textDecorationLine: 'underline',
  },
  signUpButton: {
    backgroundColor: '#2563eb',
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
    minHeight: 48,
  },
  signUpButtonDisabled: {
    backgroundColor: '#94a3b8',
  },
  signUpButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  loginContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
  },
  loginText: {
    color: '#64748b',
    fontSize: 14,
  },
  loginLink: {
    color: '#2563eb',
    fontSize: 14,
    fontWeight: '600',
  },
  coppaNotice: {
    backgroundColor: '#f1f5f9',
    borderRadius: 8,
    padding: 16,
    marginTop: 'auto',
  },
  coppaText: {
    color: '#475569',
    fontSize: 12,
    lineHeight: 18,
    textAlign: 'center',
  },
});
