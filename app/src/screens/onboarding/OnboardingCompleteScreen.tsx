/**
 * OnboardingCompleteScreen.tsx
 *
 * Success screen shown after completing onboarding
 * Celebrates completion and navigates to main app
 */

import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Animated,
} from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

type Props = NativeStackScreenProps<any, 'OnboardingComplete'>;

export function OnboardingCompleteScreen({ navigation }: Props): React.JSX.Element {
  const fadeAnim = React.useRef(new Animated.Value(0)).current;
  const scaleAnim = React.useRef(new Animated.Value(0.5)).current;

  React.useEffect(() => {
    // Animate entrance
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 600,
        useNativeDriver: true,
      }),
      Animated.spring(scaleAnim, {
        toValue: 1,
        friction: 4,
        useNativeDriver: true,
      }),
    ]).start();
  }, [fadeAnim, scaleAnim]);

  const handleGetStarted = (): void => {
    // Navigate to main app dashboard
    navigation.reset({
      index: 0,
      routes: [{ name: 'Main' }],
    });
  };

  return (
    <View style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.content}>
          {/* Success Animation */}
          <Animated.View
            style={[
              styles.successContainer,
              {
                opacity: fadeAnim,
                transform: [{ scale: scaleAnim }],
              },
            ]}
          >
            <View style={styles.successIcon}>
              <Text style={styles.successIconText}>🎉</Text>
            </View>
            <View style={styles.checkmarkContainer}>
              <Text style={styles.checkmark}>✓</Text>
            </View>
          </Animated.View>

          {/* Success Message */}
          <View style={styles.messageSection}>
            <Text style={styles.title}>You're All Set!</Text>
            <Text style={styles.subtitle}>
              Your EduLens account is ready. Let's start your child's learning adventure!
            </Text>
          </View>

          {/* Summary Cards */}
          <View style={styles.summarySection}>
            <View style={styles.summaryCard}>
              <View style={styles.summaryIconContainer}>
                <Text style={styles.summaryIcon}>✓</Text>
              </View>
              <View style={styles.summaryContent}>
                <Text style={styles.summaryTitle}>Account Created</Text>
                <Text style={styles.summaryDescription}>
                  Your parent account is secure and ready
                </Text>
              </View>
            </View>

            <View style={styles.summaryCard}>
              <View style={styles.summaryIconContainer}>
                <Text style={styles.summaryIcon}>✓</Text>
              </View>
              <View style={styles.summaryContent}>
                <Text style={styles.summaryTitle}>Child Profile Set</Text>
                <Text style={styles.summaryDescription}>
                  Learning experience personalized for your child
                </Text>
              </View>
            </View>

            <View style={styles.summaryCard}>
              <View style={styles.summaryIconContainer}>
                <Text style={styles.summaryIcon}>✓</Text>
              </View>
              <View style={styles.summaryContent}>
                <Text style={styles.summaryTitle}>Ready to Connect</Text>
                <Text style={styles.summaryDescription}>
                  You can pair your device anytime from Settings
                </Text>
              </View>
            </View>
          </View>

          {/* Next Steps */}
          <View style={styles.nextStepsSection}>
            <Text style={styles.nextStepsTitle}>What's Next?</Text>

            <View style={styles.nextStepsList}>
              <View style={styles.nextStepItem}>
                <Text style={styles.nextStepIcon}>📱</Text>
                <View style={styles.nextStepContent}>
                  <Text style={styles.nextStepTitle}>Explore the Dashboard</Text>
                  <Text style={styles.nextStepDescription}>
                    View your child's learning progress and activity
                  </Text>
                </View>
              </View>

              <View style={styles.nextStepItem}>
                <Text style={styles.nextStepIcon}>⚙️</Text>
                <View style={styles.nextStepContent}>
                  <Text style={styles.nextStepTitle}>Configure Settings</Text>
                  <Text style={styles.nextStepDescription}>
                    Set up parental controls and preferences
                  </Text>
                </View>
              </View>

              <View style={styles.nextStepItem}>
                <Text style={styles.nextStepIcon}>👓</Text>
                <View style={styles.nextStepContent}>
                  <Text style={styles.nextStepTitle}>Pair EduLens Device</Text>
                  <Text style={styles.nextStepDescription}>
                    Connect the glasses when you're ready
                  </Text>
                </View>
              </View>
            </View>
          </View>

          {/* Support Information */}
          <View style={styles.supportSection}>
            <Text style={styles.supportText}>
              Need help getting started? Visit our Help Center or contact support anytime.
            </Text>
          </View>
        </View>
      </ScrollView>

      {/* Bottom Action */}
      <View style={styles.bottomAction}>
        <TouchableOpacity
          style={styles.getStartedButton}
          onPress={handleGetStarted}
        >
          <Text style={styles.getStartedButtonText}>Go to Dashboard</Text>
          <Text style={styles.getStartedButtonIcon}>→</Text>
        </TouchableOpacity>
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
    paddingTop: 40,
  },
  successContainer: {
    alignItems: 'center',
    marginBottom: 32,
    position: 'relative',
  },
  successIcon: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: '#eff6ff',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#2563eb',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.15,
    shadowRadius: 20,
    elevation: 8,
  },
  successIconText: {
    fontSize: 60,
  },
  checkmarkContainer: {
    position: 'absolute',
    bottom: -10,
    right: '50%',
    marginRight: -60,
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#10b981',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 4,
    borderColor: '#f8f9fa',
    shadowColor: '#10b981',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 6,
  },
  checkmark: {
    color: '#fff',
    fontSize: 28,
    fontWeight: 'bold',
  },
  messageSection: {
    alignItems: 'center',
    marginBottom: 40,
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
  summarySection: {
    marginBottom: 32,
  },
  summaryCard: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  summaryIconContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#d1fae5',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 16,
  },
  summaryIcon: {
    fontSize: 20,
    color: '#10b981',
    fontWeight: 'bold',
  },
  summaryContent: {
    flex: 1,
    justifyContent: 'center',
  },
  summaryTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1e293b',
    marginBottom: 4,
  },
  summaryDescription: {
    fontSize: 14,
    color: '#64748b',
    lineHeight: 20,
  },
  nextStepsSection: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 20,
    marginBottom: 24,
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
  nextStepsList: {
    gap: 16,
  },
  nextStepItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  nextStepIcon: {
    fontSize: 28,
    marginRight: 16,
  },
  nextStepContent: {
    flex: 1,
  },
  nextStepTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1e293b',
    marginBottom: 4,
  },
  nextStepDescription: {
    fontSize: 14,
    color: '#64748b',
    lineHeight: 20,
  },
  supportSection: {
    backgroundColor: '#f0f9ff',
    borderLeftWidth: 4,
    borderLeftColor: '#2563eb',
    borderRadius: 8,
    padding: 16,
    marginBottom: 20,
  },
  supportText: {
    fontSize: 14,
    color: '#1e40af',
    lineHeight: 20,
    textAlign: 'center',
  },
  bottomAction: {
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
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
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
    marginRight: 8,
  },
  getStartedButtonIcon: {
    color: '#fff',
    fontSize: 20,
    fontWeight: 'bold',
  },
});
