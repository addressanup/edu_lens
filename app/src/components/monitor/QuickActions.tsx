/**
 * QuickActions Component
 *
 * Encouragement buttons and message controls for parent interaction.
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { EncouragementType } from '../../hooks/useLiveMonitor';
import { colors } from '../../theme/colors';
import { spacing } from '../../theme/spacing';

interface QuickActionsProps {
  onEncouragement: (type: EncouragementType) => void;
  onMessage: () => void;
  onDisconnect: () => void;
}

const encouragements: Array<{ type: EncouragementType; label: string; icon: string }> = [
  { type: 'great_job', label: 'Great!', icon: '+' },
  { type: 'keep_going', label: 'Keep going!', icon: '>' },
  { type: 'proud', label: 'Proud!', icon: '<3' },
  { type: 'almost_there', label: 'Almost!', icon: '~' },
];

const QuickActions: React.FC<QuickActionsProps> = ({
  onEncouragement,
  onMessage,
  onDisconnect,
}) => {
  return (
    <View style={styles.container}>
      {/* Encouragement buttons */}
      <View style={styles.encouragementRow}>
        {encouragements.map((item) => (
          <TouchableOpacity
            key={item.type}
            style={styles.encouragementButton}
            onPress={() => onEncouragement(item.type)}
          >
            <Text style={styles.encouragementIcon}>{item.icon}</Text>
            <Text style={styles.encouragementLabel}>{item.label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Action buttons */}
      <View style={styles.actionRow}>
        <TouchableOpacity
          style={[styles.actionButton, styles.messageButton]}
          onPress={onMessage}
        >
          <Text style={styles.actionIcon}>Aa</Text>
          <Text style={styles.actionLabel}>Message</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.actionButton, styles.disconnectButton]}
          onPress={onDisconnect}
        >
          <Text style={styles.disconnectIcon}>X</Text>
          <Text style={styles.disconnectLabel}>Disconnect</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    padding: spacing.md,
    backgroundColor: colors.cardBackground,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  encouragementRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: spacing.md,
  },
  encouragementButton: {
    flex: 1,
    alignItems: 'center',
    padding: spacing.sm,
    marginHorizontal: spacing.xs,
    backgroundColor: colors.primaryLight,
    borderRadius: 12,
  },
  encouragementIcon: {
    fontSize: 20,
    marginBottom: 2,
  },
  encouragementLabel: {
    fontSize: 11,
    fontWeight: '500',
    color: colors.primary,
  },
  actionRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  actionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.md,
    borderRadius: 12,
    marginHorizontal: spacing.xs,
  },
  messageButton: {
    backgroundColor: colors.primary,
  },
  actionIcon: {
    fontSize: 16,
    color: colors.white,
    marginRight: spacing.sm,
  },
  actionLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.white,
  },
  disconnectButton: {
    backgroundColor: colors.error,
  },
  disconnectIcon: {
    fontSize: 16,
    color: colors.white,
    marginRight: spacing.sm,
    fontWeight: 'bold',
  },
  disconnectLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.white,
  },
});

export default QuickActions;
