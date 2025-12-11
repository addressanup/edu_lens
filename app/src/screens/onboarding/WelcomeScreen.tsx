/**
 * WelcomeScreen.tsx
 *
 * First screen of the onboarding flow
 * Welcomes parents and introduces the EduLens platform
 */

import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Image,
} from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { OnboardingProgress } from '../../components/onboarding/OnboardingProgress';

type Props = NativeStackScreenProps<any, 'Welcome'>;

export function WelcomeScreen({ navigation }: Props): React.JSX.Element {
  const handleGetStarted = (): void => {
    navigation.navigate('AddChild');
  };

  return (
    <View style={styles.container}>
      <OnboardingProgress currentStep={1} totalSteps={3} />

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.content}>
          {/* Hero Section */}
          <View style={styles.heroSection}>
            <View style={styles.logoContainer}>
              <Text style={styles.logoIcon}>🔍</Text>
            </View>
            <Text style={styles.title}>Welcome to EduLens</Text>
            <Text style={styles.subtitle}>
              Empowering your child's learning journey with AI-powered assistance
            </Text>
          </View>

          {/* Features Section */}
          <View style={styles.featuresSection}>
            <View style={styles.featureCard}>
              <Text style={styles.featureIcon}>👁️</Text>
              <Text style={styles.featureTitle}>Visual Learning</Text>
              <Text style={styles.featureDescription}>
                Capture and analyze text from books, worksheets, and the environment
              </Text>
            </View>

            <View style={styles.featureCard}>
              <Text style={styles.featureIcon}>🎙️</Text>
              <Text style={styles.featureTitle}>Voice Assistance</Text>
              <Text style={styles.featureDescription}>
                Natural conversation with AI to answer questions and provide guidance
              </Text>
            </View>

            <View style={styles.featureCard}>
              <Text style={styles.featureIcon}>📊</Text>
              <Text style={styles.featureTitle}>Progress Tracking</Text>
              <Text style={styles.featureDescription}>
                Monitor your child's learning activities and milestones
              </Text>
            </View>

            <View style={styles.featureCard}>
              <Text style={styles.featureIcon}>🔒</Text>
              <Text style={styles.featureTitle}>Safe & Secure</Text>
              <Text style={styles.featureDescription}>
                COPPA-compliant with robust parental controls and privacy protection
              </Text>
            </View>
          </View>

          {/* What's Next Section */}
          <View style={styles.nextStepsSection}>
            <Text style={styles.nextStepsTitle}>What's Next?</Text>
            <View style={styles.stepsList}>
              <View style={styles.stepItem}>
                <View style={styles.stepNumber}>
                  <Text style={styles.stepNumberText}>1</Text>
                </View>
                <Text style={styles.stepText}>Create your child's profile</Text>
              </View>
              <View style={styles.stepItem}>
                <View style={styles.stepNumber}>
                  <Text style={styles.stepNumberText}>2</Text>
                </View>
                <Text style={styles.stepText}>Set up and pair the EduLens device</Text>
              </View>
              <View style={styles.stepItem}>
                <View style={styles.stepNumber}>
                  <Text style={styles.stepNumberText}>3</Text>
                </View>
                <Text style={styles.stepText}>Start learning together!</Text>
              </View>
            </View>
          </View>
        </View>
      </ScrollView>

      {/* Bottom Actions */}
      <View style={styles.bottomActions}>
        <TouchableOpacity
          style={styles.getStartedButton}
          onPress={handleGetStarted}
        >
          <Text style={styles.getStartedButtonText}>Get Started</Text>
        </TouchableOpacity>

        <Text style={styles.timeEstimate}>Takes about 5 minutes</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  scrollContent: {
    flexGrow: 1,
    paddingBottom: 120,
  },
  content: {
    paddingHorizontal: 24,
    paddingTop: 20,
  },
  heroSection: {
    alignItems: 'center',
    marginBottom: 40,
  },
  logoContainer: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: '#eff6ff',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 24,
    shadowColor: '#2563eb',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 5,
  },
  logoIcon: {
    fontSize: 48,
  },
  title: {
    fontSize: 32,
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
    paddingHorizontal: 20,
  },
  featuresSection: {
    marginBottom: 40,
  },
  featureCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 20,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  featureIcon: {
    fontSize: 32,
    marginBottom: 12,
  },
  featureTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1e293b',
    marginBottom: 8,
  },
  featureDescription: {
    fontSize: 14,
    color: '#64748b',
    lineHeight: 20,
  },
  nextStepsSection: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 20,
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  nextStepsTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#1e293b',
    marginBottom: 20,
  },
  stepsList: {
    gap: 16,
  },
  stepItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  stepNumber: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#2563eb',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 16,
  },
  stepNumberText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },
  stepText: {
    flex: 1,
    fontSize: 16,
    color: '#334155',
    lineHeight: 22,
  },
  bottomActions: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: '#fff',
    paddingHorizontal: 24,
    paddingTop: 16,
    paddingBottom: 32,
    borderTopWidth: 1,
    borderTopColor: '#e2e8f0',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 5,
  },
  getStartedButton: {
    backgroundColor: '#2563eb',
    borderRadius: 8,
    paddingVertical: 16,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
    shadowColor: '#2563eb',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 4,
  },
  getStartedButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  timeEstimate: {
    textAlign: 'center',
    fontSize: 14,
    color: '#64748b',
  },
});
