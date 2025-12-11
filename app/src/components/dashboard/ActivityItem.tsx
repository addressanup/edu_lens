/**
 * ActivityItem Component
 * Displays a single learning activity/session in a list
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { LearningActivity } from '../../types';

interface ActivityItemProps {
  activity: LearningActivity;
  onPress?: () => void;
  style?: any;
}

const ACTIVITY_ICONS: Record<string, string> = {
  reading: '📖',
  tutoring: '👨‍🏫',
  translation: '🌐',
  ocr: '📷',
  exploration: '🔍',
  default: '📝',
};

const ACTIVITY_COLORS: Record<string, string> = {
  reading: '#4CAF50',
  tutoring: '#2196F3',
  translation: '#9C27B0',
  ocr: '#FF9800',
  exploration: '#00BCD4',
  default: '#4A90A4',
};

export const ActivityItem: React.FC<ActivityItemProps> = ({
  activity,
  onPress,
  style,
}) => {
  const icon = ACTIVITY_ICONS[activity.type] || ACTIVITY_ICONS.default;
  const color = ACTIVITY_COLORS[activity.type] || ACTIVITY_COLORS.default;

  const formatDuration = (seconds: number): string => {
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    if (remainingSeconds === 0) return `${minutes}m`;
    return `${minutes}m ${remainingSeconds}s`;
  };

  const formatTime = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const getEngagementLevel = (engagement: number): { text: string; color: string } => {
    if (engagement >= 80) return { text: 'High', color: '#4CAF50' };
    if (engagement >= 60) return { text: 'Medium', color: '#FF9800' };
    return { text: 'Low', color: '#F44336' };
  };

  const engagementLevel = getEngagementLevel(activity.engagement);

  const content = (
    <>
      <View style={[styles.iconContainer, { backgroundColor: `${color}20` }]}>
        <Text style={styles.icon}>{icon}</Text>
      </View>

      <View style={styles.content}>
        <View style={styles.topRow}>
          <Text style={styles.type} numberOfLines={1}>
            {activity.type.charAt(0).toUpperCase() + activity.type.slice(1)}
          </Text>
          <Text style={styles.time}>{formatTime(activity.startTime)}</Text>
        </View>

        {activity.subject && (
          <Text style={styles.subject} numberOfLines={1}>
            {activity.subject}
            {activity.topic && ` • ${activity.topic}`}
          </Text>
        )}

        <View style={styles.stats}>
          <View style={styles.statBadge}>
            <Text style={styles.statText}>⏱ {formatDuration(activity.duration)}</Text>
          </View>
          {activity.questionsAsked > 0 && (
            <View style={styles.statBadge}>
              <Text style={styles.statText}>❓ {activity.questionsAsked}</Text>
            </View>
          )}
          <View style={styles.statBadge}>
            <Text style={[styles.statText, { color: engagementLevel.color }]}>
              {engagementLevel.text} Engagement
            </Text>
          </View>
        </View>
      </View>
    </>
  );

  if (onPress) {
    return (
      <TouchableOpacity
        style={[styles.container, style]}
        onPress={onPress}
        activeOpacity={0.7}
      >
        {content}
      </TouchableOpacity>
    );
  }

  return <View style={[styles.container, style]}>{content}</View>;
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    backgroundColor: '#FFFFFF',
    padding: 12,
    borderRadius: 12,
    marginBottom: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 2,
  },
  iconContainer: {
    width: 48,
    height: 48,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  icon: {
    fontSize: 24,
  },
  content: {
    flex: 1,
  },
  topRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  type: {
    fontSize: 15,
    fontWeight: '600',
    color: '#333333',
    flex: 1,
  },
  time: {
    fontSize: 12,
    color: '#999999',
    marginLeft: 8,
  },
  subject: {
    fontSize: 13,
    color: '#666666',
    marginBottom: 8,
  },
  stats: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  statBadge: {
    backgroundColor: '#F5F5F5',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  statText: {
    fontSize: 11,
    color: '#666666',
    fontWeight: '500',
  },
});
