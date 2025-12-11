/**
 * SubjectCard Component
 * Displays progress for a specific subject with mastery level
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { SubjectProgress } from '../../types';

interface SubjectCardProps {
  subject: SubjectProgress;
  onPress?: () => void;
  style?: any;
}

const SUBJECT_COLORS: Record<string, string> = {
  Math: '#2196F3',
  Reading: '#4CAF50',
  Science: '#FF9800',
  'Social Studies': '#9C27B0',
  Language: '#00BCD4',
  Writing: '#F44336',
  default: '#4A90A4',
};

const SUBJECT_ICONS: Record<string, string> = {
  Math: '🔢',
  Reading: '📚',
  Science: '🔬',
  'Social Studies': '🌍',
  Language: '🗣️',
  Writing: '✍️',
  default: '📖',
};

export const SubjectCard: React.FC<SubjectCardProps> = ({
  subject,
  onPress,
  style,
}) => {
  const color = SUBJECT_COLORS[subject.subject] || SUBJECT_COLORS.default;
  const icon = SUBJECT_ICONS[subject.subject] || SUBJECT_ICONS.default;
  const durationMinutes = Math.floor(subject.duration / 60);
  const improvementText =
    subject.improvement > 0
      ? `+${subject.improvement}%`
      : `${subject.improvement}%`;

  const getMasteryLevel = (confidence: number): string => {
    if (confidence >= 90) return 'Mastery';
    if (confidence >= 75) return 'Proficient';
    if (confidence >= 60) return 'Developing';
    return 'Beginning';
  };

  const masteryLevel = getMasteryLevel(subject.confidenceLevel);

  const content = (
    <>
      <View style={styles.header}>
        <View style={[styles.iconContainer, { backgroundColor: `${color}20` }]}>
          <Text style={styles.icon}>{icon}</Text>
        </View>
        <View style={styles.headerRight}>
          {subject.improvement !== 0 && (
            <View
              style={[
                styles.improvementBadge,
                {
                  backgroundColor:
                    subject.improvement > 0 ? '#E8F5E9' : '#FFEBEE',
                },
              ]}
            >
              <Text
                style={[
                  styles.improvementText,
                  {
                    color: subject.improvement > 0 ? '#4CAF50' : '#F44336',
                  },
                ]}
              >
                {improvementText}
              </Text>
            </View>
          )}
        </View>
      </View>

      <Text style={styles.subjectName}>{subject.subject}</Text>

      <View style={styles.stats}>
        <View style={styles.statItem}>
          <Text style={styles.statLabel}>Time Spent</Text>
          <Text style={styles.statValue}>{durationMinutes} min</Text>
        </View>
        <View style={styles.statItem}>
          <Text style={styles.statLabel}>Questions</Text>
          <Text style={styles.statValue}>{subject.questionsAsked}</Text>
        </View>
      </View>

      <View style={styles.masterySection}>
        <View style={styles.masteryHeader}>
          <Text style={styles.masteryLabel}>Mastery Level</Text>
          <Text style={[styles.masteryLevel, { color }]}>{masteryLevel}</Text>
        </View>
        <View style={styles.progressBarContainer}>
          <View
            style={[
              styles.progressBar,
              {
                width: `${subject.confidenceLevel}%`,
                backgroundColor: color,
              },
            ]}
          />
        </View>
        <Text style={styles.confidenceText}>
          {subject.confidenceLevel}% Confidence
        </Text>
      </View>
    </>
  );

  if (onPress) {
    return (
      <TouchableOpacity
        style={[styles.card, style]}
        onPress={onPress}
        activeOpacity={0.7}
      >
        {content}
      </TouchableOpacity>
    );
  }

  return <View style={[styles.card, style]}>{content}</View>;
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  iconContainer: {
    width: 48,
    height: 48,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  icon: {
    fontSize: 24,
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  improvementBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  improvementText: {
    fontSize: 12,
    fontWeight: '600',
  },
  subjectName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333333',
    marginBottom: 16,
  },
  stats: {
    flexDirection: 'row',
    marginBottom: 16,
    gap: 16,
  },
  statItem: {
    flex: 1,
  },
  statLabel: {
    fontSize: 12,
    color: '#666666',
    marginBottom: 4,
  },
  statValue: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333333',
  },
  masterySection: {
    marginTop: 8,
  },
  masteryHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  masteryLabel: {
    fontSize: 13,
    color: '#666666',
  },
  masteryLevel: {
    fontSize: 13,
    fontWeight: '600',
  },
  progressBarContainer: {
    height: 8,
    backgroundColor: '#F0F0F0',
    borderRadius: 4,
    overflow: 'hidden',
    marginBottom: 6,
  },
  progressBar: {
    height: '100%',
    borderRadius: 4,
  },
  confidenceText: {
    fontSize: 11,
    color: '#999999',
    textAlign: 'right',
  },
});
