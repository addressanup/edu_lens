/**
 * ActivityFeed Component
 *
 * Displays real-time activity events from the observation session.
 */

import React from 'react';
import { View, Text, StyleSheet, FlatList } from 'react-native';
import { ObservationEvent } from '../../services/realtimeStream';
import { colors } from '../../theme/colors';
import { spacing } from '../../theme/spacing';

interface ActivityFeedProps {
  events: ObservationEvent[];
}

const getEventIcon = (type: string): string => {
  switch (type) {
    case 'struggle_detected':
      return '!';
    case 'intervention':
      return '?';
    case 'scene_change':
      return '*';
    case 'parent_message_sent':
    case 'parent_message':
      return '>';
    case 'encouragement_sent':
    case 'encouragement':
      return '+';
    case 'parent_voice_sent':
      return 'M';
    case 'parent_connected':
      return '@';
    case 'parent_disconnected':
      return 'x';
    default:
      return '-';
  }
};

const getEventLabel = (type: string): string => {
  switch (type) {
    case 'struggle_detected':
      return 'Struggle Detected';
    case 'intervention':
      return 'AI Offered Help';
    case 'scene_change':
      return 'Scene Changed';
    case 'parent_message_sent':
      return 'You Sent Message';
    case 'parent_message':
      return 'Parent Message';
    case 'encouragement_sent':
      return 'You Sent Encouragement';
    case 'encouragement':
      return 'Encouragement';
    case 'parent_voice_sent':
      return 'You Sent Voice';
    case 'parent_connected':
      return 'Parent Connected';
    case 'parent_disconnected':
      return 'Parent Disconnected';
    default:
      return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }
};

const getEventColor = (type: string): string => {
  switch (type) {
    case 'struggle_detected':
      return colors.warning;
    case 'intervention':
      return colors.info;
    case 'encouragement_sent':
    case 'encouragement':
      return colors.success;
    case 'parent_message_sent':
    case 'parent_voice_sent':
      return colors.primary;
    default:
      return colors.textSecondary;
  }
};

const formatTime = (timestamp: number): string => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const ActivityFeed: React.FC<ActivityFeedProps> = ({ events }) => {
  const renderItem = ({ item }: { item: ObservationEvent }) => {
    const color = getEventColor(item.type);

    return (
      <View style={styles.eventItem}>
        <View style={[styles.eventIcon, { backgroundColor: color }]}>
          <Text style={styles.eventIconText}>{getEventIcon(item.type)}</Text>
        </View>
        <View style={styles.eventContent}>
          <Text style={styles.eventLabel}>{getEventLabel(item.type)}</Text>
          {item.payload?.text && (
            <Text style={styles.eventText} numberOfLines={2}>
              {String(item.payload.text)}
            </Text>
          )}
          {item.payload?.message && (
            <Text style={styles.eventText} numberOfLines={2}>
              {String(item.payload.message)}
            </Text>
          )}
        </View>
        <Text style={styles.eventTime}>{formatTime(item.timestamp)}</Text>
      </View>
    );
  };

  if (events.length === 0) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Activity</Text>
        <View style={styles.emptyState}>
          <Text style={styles.emptyText}>No activity yet</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Activity</Text>
      <FlatList
        data={events}
        renderItem={renderItem}
        keyExtractor={(item, index) => `${item.type}-${item.timestamp}-${index}`}
        style={styles.list}
        scrollEnabled={false}
        showsVerticalScrollIndicator={false}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    margin: spacing.md,
    backgroundColor: colors.cardBackground,
    borderRadius: 12,
    padding: spacing.md,
  },
  title: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
    marginBottom: spacing.sm,
  },
  list: {
    maxHeight: 200,
  },
  emptyState: {
    paddingVertical: spacing.lg,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 14,
    color: colors.textSecondary,
  },
  eventItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  eventIcon: {
    width: 28,
    height: 28,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: spacing.sm,
  },
  eventIconText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: colors.white,
  },
  eventContent: {
    flex: 1,
  },
  eventLabel: {
    fontSize: 14,
    fontWeight: '500',
    color: colors.text,
  },
  eventText: {
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 2,
  },
  eventTime: {
    fontSize: 12,
    color: colors.textSecondary,
  },
});

export default ActivityFeed;
