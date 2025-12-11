/**
 * SafetyToggle Component
 * Toggle component for safety and privacy settings
 */

import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ViewStyle,
} from 'react-native';

export type SafetyLevel = 'critical' | 'important' | 'optional';

export interface SafetySetting {
  id: string;
  title: string;
  description: string;
  enabled: boolean;
  level: SafetyLevel;
  icon?: string;
  locked?: boolean; // Some settings might be locked based on subscription
}

interface SafetyToggleProps {
  setting: SafetySetting;
  onToggle: (settingId: string, enabled: boolean) => void;
  disabled?: boolean;
  style?: ViewStyle;
}

export const SafetyToggle: React.FC<SafetyToggleProps> = ({
  setting,
  onToggle,
  disabled = false,
  style,
}) => {
  const handleToggle = () => {
    if (!disabled && !setting.locked) {
      onToggle(setting.id, !setting.enabled);
    }
  };

  const getLevelColor = (): string => {
    switch (setting.level) {
      case 'critical':
        return '#FF5252';
      case 'important':
        return '#FFA726';
      case 'optional':
        return '#4A90A4';
      default:
        return '#999999';
    }
  };

  const getLevelLabel = (): string => {
    switch (setting.level) {
      case 'critical':
        return 'Critical';
      case 'important':
        return 'Important';
      case 'optional':
        return 'Optional';
      default:
        return '';
    }
  };

  return (
    <View style={[styles.container, style]}>
      <TouchableOpacity
        style={styles.content}
        onPress={handleToggle}
        disabled={disabled || setting.locked}
        activeOpacity={0.7}
      >
        <View style={styles.main}>
          <View style={styles.header}>
            <Text
              style={[
                styles.title,
                (disabled || setting.locked) && styles.disabledText,
              ]}
            >
              {setting.title}
            </Text>
            {setting.locked && (
              <View style={styles.lockBadge}>
                <Text style={styles.lockText}>🔒</Text>
              </View>
            )}
          </View>

          <Text style={styles.description}>{setting.description}</Text>

          <View style={styles.footer}>
            <View style={[styles.levelBadge, { backgroundColor: `${getLevelColor()}20` }]}>
              <Text style={[styles.levelText, { color: getLevelColor() }]}>
                {getLevelLabel()}
              </Text>
            </View>
          </View>
        </View>

        <View
          style={[
            styles.toggle,
            setting.enabled && styles.toggleActive,
            (disabled || setting.locked) && styles.toggleDisabled,
          ]}
        >
          <View
            style={[
              styles.toggleThumb,
              setting.enabled && styles.toggleThumbActive,
            ]}
          />
        </View>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 1,
    },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
  },
  main: {
    flex: 1,
    marginRight: 16,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
  },
  title: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333333',
    flex: 1,
  },
  lockBadge: {
    marginLeft: 8,
  },
  lockText: {
    fontSize: 14,
  },
  description: {
    fontSize: 14,
    color: '#666666',
    lineHeight: 20,
    marginBottom: 8,
  },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  levelBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  levelText: {
    fontSize: 12,
    fontWeight: '600',
  },
  disabledText: {
    color: '#CCCCCC',
  },
  toggle: {
    width: 51,
    height: 31,
    borderRadius: 15.5,
    backgroundColor: '#E0E0E0',
    padding: 2,
    justifyContent: 'center',
  },
  toggleActive: {
    backgroundColor: '#4A90A4',
  },
  toggleDisabled: {
    backgroundColor: '#F0F0F0',
  },
  toggleThumb: {
    width: 27,
    height: 27,
    borderRadius: 13.5,
    backgroundColor: '#FFFFFF',
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.2,
    shadowRadius: 2,
    elevation: 2,
  },
  toggleThumbActive: {
    alignSelf: 'flex-end',
  },
});
