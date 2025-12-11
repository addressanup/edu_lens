/**
 * AchievementBadge Component
 * Displays an achievement badge with rarity and unlock status
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Achievement } from '../../types';

interface AchievementBadgeProps {
  achievement: Achievement;
  locked?: boolean;
  progress?: number; // 0-100 for locked achievements
  onPress?: () => void;
  size?: 'small' | 'medium' | 'large';
  style?: any;
}

const RARITY_COLORS: Record<string, { bg: string; border: string; glow: string }> = {
  common: {
    bg: '#E8F5E9',
    border: '#4CAF50',
    glow: '#4CAF5020',
  },
  rare: {
    bg: '#E3F2FD',
    border: '#2196F3',
    glow: '#2196F320',
  },
  epic: {
    bg: '#F3E5F5',
    border: '#9C27B0',
    glow: '#9C27B020',
  },
  legendary: {
    bg: '#FFF8E1',
    border: '#FFC107',
    glow: '#FFC10730',
  },
};

const SIZE_CONFIG = {
  small: { container: 80, icon: 32, nameSize: 11, descSize: 9 },
  medium: { container: 100, icon: 40, nameSize: 13, descSize: 10 },
  large: { container: 120, icon: 48, nameSize: 15, descSize: 11 },
};

export const AchievementBadge: React.FC<AchievementBadgeProps> = ({
  achievement,
  locked = false,
  progress = 0,
  onPress,
  size = 'medium',
  style,
}) => {
  const colors = RARITY_COLORS[achievement.rarity] || RARITY_COLORS.common;
  const sizeConfig = SIZE_CONFIG[size];

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const content = (
    <>
      <View
        style={[
          styles.badgeContainer,
          {
            width: sizeConfig.container,
            height: sizeConfig.container,
            backgroundColor: locked ? '#F5F5F5' : colors.bg,
            borderColor: locked ? '#CCCCCC' : colors.border,
          },
          !locked && { shadowColor: colors.border },
        ]}
      >
        <Text
          style={[
            styles.icon,
            { fontSize: sizeConfig.icon, opacity: locked ? 0.3 : 1 },
          ]}
        >
          {locked ? '🔒' : achievement.icon}
        </Text>
        {!locked && achievement.rarity === 'legendary' && (
          <View style={styles.sparkle}>
            <Text style={styles.sparkleText}>✨</Text>
          </View>
        )}
      </View>

      <Text
        style={[
          styles.achievementName,
          { fontSize: sizeConfig.nameSize },
          locked && styles.lockedText,
        ]}
        numberOfLines={2}
      >
        {achievement.title}
      </Text>

      {locked && progress > 0 && (
        <View style={styles.progressContainer}>
          <View style={styles.progressBar}>
            <View
              style={[
                styles.progressFill,
                {
                  width: `${progress}%`,
                  backgroundColor: colors.border,
                },
              ]}
            />
          </View>
          <Text style={styles.progressText}>{progress}%</Text>
        </View>
      )}

      {!locked && (
        <Text style={[styles.date, { fontSize: sizeConfig.descSize }]}>
          {formatDate(achievement.earnedAt)}
        </Text>
      )}

      {!locked && size !== 'small' && (
        <View style={[styles.rarityBadge, { backgroundColor: colors.bg }]}>
          <Text style={[styles.rarityText, { color: colors.border }]}>
            {achievement.rarity.toUpperCase()}
          </Text>
        </View>
      )}
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
    alignItems: 'center',
    padding: 8,
  },
  badgeContainer: {
    borderRadius: 16,
    borderWidth: 3,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 4,
    position: 'relative',
  },
  icon: {
    textAlign: 'center',
  },
  sparkle: {
    position: 'absolute',
    top: -8,
    right: -8,
  },
  sparkleText: {
    fontSize: 20,
  },
  achievementName: {
    fontWeight: '600',
    color: '#333333',
    textAlign: 'center',
    marginBottom: 4,
  },
  lockedText: {
    color: '#999999',
  },
  date: {
    color: '#999999',
    textAlign: 'center',
  },
  rarityBadge: {
    marginTop: 6,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 8,
  },
  rarityText: {
    fontSize: 9,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  progressContainer: {
    width: '100%',
    marginTop: 4,
  },
  progressBar: {
    height: 4,
    backgroundColor: '#E0E0E0',
    borderRadius: 2,
    overflow: 'hidden',
    marginBottom: 2,
  },
  progressFill: {
    height: '100%',
    borderRadius: 2,
  },
  progressText: {
    fontSize: 9,
    color: '#999999',
    textAlign: 'center',
  },
});
