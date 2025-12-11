/**
 * OnboardingProgress.tsx
 *
 * Progress indicator component for onboarding flow
 * Shows current step and total steps
 */

import React from 'react';
import {
  View,
  Text,
  StyleSheet,
} from 'react-native';

interface OnboardingProgressProps {
  currentStep: number;
  totalSteps: number;
}

export function OnboardingProgress({
  currentStep,
  totalSteps,
}: OnboardingProgressProps): React.JSX.Element {
  const progress = (currentStep / totalSteps) * 100;

  return (
    <View style={styles.container}>
      {/* Progress Bar */}
      <View style={styles.progressBarContainer}>
        <View style={[styles.progressBarFill, { width: `${progress}%` }]} />
      </View>

      {/* Step Indicator */}
      <View style={styles.stepIndicator}>
        <View style={styles.stepDots}>
          {Array.from({ length: totalSteps }, (_, index) => {
            const stepNumber = index + 1;
            const isCompleted = stepNumber < currentStep;
            const isCurrent = stepNumber === currentStep;

            return (
              <View
                key={stepNumber}
                style={[
                  styles.stepDot,
                  isCurrent && styles.stepDotActive,
                  isCompleted && styles.stepDotCompleted,
                ]}
              >
                {isCompleted && (
                  <Text style={styles.checkmark}>✓</Text>
                )}
              </View>
            );
          })}
        </View>

        <Text style={styles.stepText}>
          Step {currentStep} of {totalSteps}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#fff',
    paddingHorizontal: 24,
    paddingTop: 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
  },
  progressBarContainer: {
    height: 4,
    backgroundColor: '#e2e8f0',
    borderRadius: 2,
    overflow: 'hidden',
    marginBottom: 16,
  },
  progressBarFill: {
    height: '100%',
    backgroundColor: '#2563eb',
    borderRadius: 2,
  },
  stepIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  stepDots: {
    flexDirection: 'row',
    gap: 8,
  },
  stepDot: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: '#e2e8f0',
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepDotActive: {
    backgroundColor: '#2563eb',
  },
  stepDotCompleted: {
    backgroundColor: '#10b981',
  },
  checkmark: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
  },
  stepText: {
    fontSize: 14,
    color: '#64748b',
    fontWeight: '600',
  },
});
