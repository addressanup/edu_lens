/**
 * SessionStats Component
 *
 * Displays session statistics like duration, subject, and problem count.
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { SessionStats as SessionStatsType } from '../../services/realtimeStream';
import { colors } from '../../theme/colors';
import { spacing } from '../../theme/spacing';

interface SessionStatsProps {
  stats: SessionStatsType | null;
}

const formatDuration = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

const SessionStats: React.FC<SessionStatsProps> = ({ stats }) => {
  if (!stats) {
    return null;
  }

  return (
    <View style={styles.container}>
      <View style={styles.statItem}>
        <Text style={styles.statLabel}>Time</Text>
        <Text style={styles.statValue}>{formatDuration(stats.duration || 0)}</Text>
      </View>

      {stats.currentSubject && (
        <View style={styles.statItem}>
          <Text style={styles.statLabel}>Subject</Text>
          <Text style={styles.statValue}>{stats.currentSubject}</Text>
        </View>
      )}

      {stats.currentProblem !== undefined && (
        <View style={styles.statItem}>
          <Text style={styles.statLabel}>Problem</Text>
          <Text style={styles.statValue}>{stats.currentProblem}</Text>
        </View>
      )}

      <View style={styles.statItem}>
        <Text style={styles.statLabel}>Frames</Text>
        <Text style={styles.statValue}>{stats.frameCount || 0}</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginHorizontal: spacing.md,
    marginVertical: spacing.sm,
    padding: spacing.md,
    backgroundColor: colors.cardBackground,
    borderRadius: 12,
  },
  statItem: {
    alignItems: 'center',
  },
  statLabel: {
    fontSize: 12,
    color: colors.textSecondary,
    marginBottom: 2,
  },
  statValue: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
  },
});

export default SessionStats;
