/**
 * AddChildScreen.tsx
 *
 * Screen for adding a child profile during onboarding
 * Features:
 * - Child information collection (name, age, grade)
 * - COPPA-compliant parental consent
 * - Optional profile photo
 * - Input validation
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useAuth } from '../../auth/AuthContext';
import { ConsentForm } from '../../components/auth/ConsentForm';
import { OnboardingProgress } from '../../components/onboarding/OnboardingProgress';
import { LanguagePicker } from '../../components/common/LanguagePicker';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

type Props = NativeStackScreenProps<any, 'AddChild'>;

interface ChildFormData {
  name: string;
  age: string;
  grade: string;
  language: string;  // Preferred language for tutoring
}

interface FormErrors {
  name?: string;
  age?: string;
  grade?: string;
}

const GRADE_OPTIONS = [
  'Pre-K',
  'Kindergarten',
  '1st Grade',
  '2nd Grade',
  '3rd Grade',
  '4th Grade',
  '5th Grade',
  '6th Grade',
  '7th Grade',
  '8th Grade',
  '9th Grade',
  '10th Grade',
  '11th Grade',
  '12th Grade',
];

export function AddChildScreen({ navigation }: Props): React.JSX.Element {
  const { addChild } = useAuth();
  const [formData, setFormData] = useState<ChildFormData>({
    name: '',
    age: '',
    grade: '',
    language: 'en',  // Default to English
  });
  const [consentGiven, setConsentGiven] = useState(false);
  const [showConsentForm, setShowConsentForm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<FormErrors>({});
  const [showGradePicker, setShowGradePicker] = useState(false);

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    // Name validation
    if (!formData.name.trim()) {
      newErrors.name = "Child's name is required";
    } else if (formData.name.trim().length < 2) {
      newErrors.name = 'Name must be at least 2 characters';
    }

    // Age validation
    const age = parseInt(formData.age);
    if (!formData.age) {
      newErrors.age = 'Age is required';
    } else if (isNaN(age) || age < 3 || age > 18) {
      newErrors.age = 'Age must be between 3 and 18';
    }

    // Grade validation
    if (!formData.grade) {
      newErrors.grade = 'Grade level is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleContinue = (): void => {
    if (!validateForm()) {
      return;
    }

    // Show consent form if not already given
    if (!consentGiven) {
      setShowConsentForm(true);
    } else {
      handleSaveChild();
    }
  };

  const handleConsentApproved = (): void => {
    setConsentGiven(true);
    setShowConsentForm(false);
    handleSaveChild();
  };

  const handleConsentDeclined = (): void => {
    setShowConsentForm(false);
    Alert.alert(
      'Consent Required',
      'Parental consent is required to create a child profile and use EduLens. This is mandated by COPPA to protect children\'s privacy.',
      [{ text: 'OK' }]
    );
  };

  const handleSaveChild = async (): Promise<void> => {
    setIsLoading(true);
    try {
      await addChild({
        name: formData.name.trim(),
        age: parseInt(formData.age),
        grade: formData.grade,
        language: formData.language,  // Include preferred language
      });

      // Navigate to device setup
      navigation.navigate('SetupDevice');
    } catch (error) {
      Alert.alert(
        'Error',
        error instanceof Error ? error.message : 'Unable to create child profile. Please try again.',
        [{ text: 'OK' }]
      );
    } finally {
      setIsLoading(false);
    }
  };

  const updateFormField = (field: keyof ChildFormData, value: string): void => {
    setFormData({ ...formData, [field]: value });

    // Clear error for this field
    if (errors[field]) {
      setErrors({ ...errors, [field]: undefined });
    }
  };

  const selectGrade = (grade: string): void => {
    updateFormField('grade', grade);
    setShowGradePicker(false);
  };

  if (showConsentForm) {
    return (
      <ConsentForm
        childName={formData.name}
        onApprove={handleConsentApproved}
        onDecline={handleConsentDeclined}
      />
    );
  }

  return (
    <View style={styles.container}>
      <OnboardingProgress currentStep={2} totalSteps={3} />

      <KeyboardAvoidingView
        style={styles.keyboardView}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 64 : 0}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.header}>
            <Text style={styles.title}>Add Your Child</Text>
            <Text style={styles.subtitle}>
              Tell us about your child to personalize their learning experience
            </Text>
          </View>

          <View style={styles.form}>
            {/* Child's Name */}
            <View style={styles.inputGroup}>
              <Text style={styles.label}>Child's Name</Text>
              <TextInput
                style={[styles.input, errors.name ? styles.inputError : null]}
                placeholder="e.g., Emma Johnson"
                placeholderTextColor="#999"
                value={formData.name}
                onChangeText={(text) => updateFormField('name', text)}
                autoCapitalize="words"
                autoComplete="name"
                editable={!isLoading}
              />
              {errors.name && <Text style={styles.errorText}>{errors.name}</Text>}
            </View>

            {/* Age */}
            <View style={styles.inputGroup}>
              <Text style={styles.label}>Age</Text>
              <TextInput
                style={[styles.input, errors.age ? styles.inputError : null]}
                placeholder="e.g., 8"
                placeholderTextColor="#999"
                value={formData.age}
                onChangeText={(text) => updateFormField('age', text.replace(/[^0-9]/g, ''))}
                keyboardType="number-pad"
                maxLength={2}
                editable={!isLoading}
              />
              <Text style={styles.helperText}>
                EduLens is designed for children ages 3-18
              </Text>
              {errors.age && <Text style={styles.errorText}>{errors.age}</Text>}
            </View>

            {/* Grade Level */}
            <View style={styles.inputGroup}>
              <Text style={styles.label}>Grade Level</Text>
              <TouchableOpacity
                style={[styles.input, styles.pickerInput, errors.grade ? styles.inputError : null]}
                onPress={() => setShowGradePicker(!showGradePicker)}
                disabled={isLoading}
              >
                <Text style={[styles.pickerText, !formData.grade && styles.pickerPlaceholder]}>
                  {formData.grade || 'Select grade level'}
                </Text>
                <Text style={styles.pickerArrow}>{showGradePicker ? '▲' : '▼'}</Text>
              </TouchableOpacity>
              {errors.grade && <Text style={styles.errorText}>{errors.grade}</Text>}

              {/* Grade Picker */}
              {showGradePicker && (
                <View style={styles.gradePicker}>
                  <ScrollView style={styles.gradePickerScroll} nestedScrollEnabled>
                    {GRADE_OPTIONS.map((grade) => (
                      <TouchableOpacity
                        key={grade}
                        style={[
                          styles.gradeOption,
                          formData.grade === grade && styles.gradeOptionSelected,
                        ]}
                        onPress={() => selectGrade(grade)}
                      >
                        <Text
                          style={[
                            styles.gradeOptionText,
                            formData.grade === grade && styles.gradeOptionTextSelected,
                          ]}
                        >
                          {grade}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </ScrollView>
                </View>
              )}
            </View>

            {/* Language Selection */}
            <LanguagePicker
              selectedLanguage={formData.language}
              onSelectLanguage={(lang) => setFormData({ ...formData, language: lang })}
              label="Preferred Language"
              disabled={isLoading}
            />
            <Text style={styles.helperText}>
              EduLens will speak and respond in this language
            </Text>

            {/* Optional Photo Section */}
            <View style={styles.photoSection}>
              <Text style={styles.label}>Profile Photo (Optional)</Text>
              <TouchableOpacity
                style={styles.photoButton}
                onPress={() => Alert.alert('Coming Soon', 'Photo upload will be available soon')}
                disabled={isLoading}
              >
                <Text style={styles.photoIcon}>📷</Text>
                <Text style={styles.photoButtonText}>Add Photo</Text>
              </TouchableOpacity>
            </View>

            {/* Privacy Notice */}
            <View style={styles.privacyNotice}>
              <Text style={styles.privacyIcon}>🔒</Text>
              <Text style={styles.privacyText}>
                Your child's information is protected and will only be used to personalize their
                learning experience. You'll be asked to provide COPPA-compliant consent on the next step.
              </Text>
            </View>
          </View>
        </ScrollView>

        {/* Bottom Actions */}
        <View style={styles.bottomActions}>
          <TouchableOpacity
            style={styles.backButton}
            onPress={() => navigation.goBack()}
            disabled={isLoading}
          >
            <Text style={styles.backButtonText}>← Back</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.continueButton, isLoading && styles.continueButtonDisabled]}
            onPress={handleContinue}
            disabled={isLoading}
          >
            {isLoading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.continueButtonText}>Continue</Text>
            )}
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  keyboardView: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    paddingHorizontal: 24,
    paddingTop: 20,
    paddingBottom: 120,
  },
  header: {
    marginBottom: 32,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#1e293b',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#64748b',
    lineHeight: 24,
  },
  form: {
    width: '100%',
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
  helperText: {
    color: '#64748b',
    fontSize: 12,
    marginTop: 4,
  },
  pickerInput: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  pickerText: {
    fontSize: 16,
    color: '#1e293b',
  },
  pickerPlaceholder: {
    color: '#999',
  },
  pickerArrow: {
    fontSize: 12,
    color: '#64748b',
  },
  gradePicker: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#cbd5e1',
    borderRadius: 8,
    marginTop: 8,
    maxHeight: 200,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  gradePickerScroll: {
    maxHeight: 200,
  },
  gradeOption: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f1f5f9',
  },
  gradeOptionSelected: {
    backgroundColor: '#eff6ff',
  },
  gradeOptionText: {
    fontSize: 16,
    color: '#334155',
  },
  gradeOptionTextSelected: {
    color: '#2563eb',
    fontWeight: '600',
  },
  photoSection: {
    marginBottom: 24,
  },
  photoButton: {
    backgroundColor: '#fff',
    borderWidth: 2,
    borderColor: '#cbd5e1',
    borderStyle: 'dashed',
    borderRadius: 8,
    paddingVertical: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  photoIcon: {
    fontSize: 32,
    marginBottom: 8,
  },
  photoButtonText: {
    fontSize: 14,
    color: '#64748b',
    fontWeight: '600',
  },
  privacyNotice: {
    flexDirection: 'row',
    backgroundColor: '#f0f9ff',
    borderLeftWidth: 4,
    borderLeftColor: '#2563eb',
    borderRadius: 8,
    padding: 16,
    marginTop: 8,
  },
  privacyIcon: {
    fontSize: 20,
    marginRight: 12,
  },
  privacyText: {
    flex: 1,
    fontSize: 13,
    color: '#1e40af',
    lineHeight: 20,
  },
  bottomActions: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    backgroundColor: '#fff',
    paddingHorizontal: 24,
    paddingTop: 16,
    paddingBottom: 32,
    borderTopWidth: 1,
    borderTopColor: '#e2e8f0',
    gap: 12,
  },
  backButton: {
    flex: 1,
    paddingVertical: 14,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#cbd5e1',
    borderRadius: 8,
  },
  backButtonText: {
    color: '#64748b',
    fontSize: 16,
    fontWeight: '600',
  },
  continueButton: {
    flex: 2,
    backgroundColor: '#2563eb',
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 48,
  },
  continueButtonDisabled: {
    backgroundColor: '#94a3b8',
  },
  continueButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
