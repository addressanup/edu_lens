/**
 * SubjectToggle Component
 * Toggle component for enabling/disabling subjects
 */

import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ViewStyle,
} from 'react-native';

export interface Subject {
  id: string;
  name: string;
  icon?: string;
  description?: string;
  enabled: boolean;
}

interface SubjectToggleProps {
  subject: Subject;
  onToggle: (subjectId: string, enabled: boolean) => void;
  disabled?: boolean;
  style?: ViewStyle;
}

export const SubjectToggle: React.FC<SubjectToggleProps> = ({
  subject,
  onToggle,
  disabled = false,
  style,
}) => {
  const handleToggle = () => {
    if (!disabled) {
      onToggle(subject.id, !subject.enabled);
    }
  };

  return (
    <View style={[styles.container, style]}>
      <TouchableOpacity
        style={styles.content}
        onPress={handleToggle}
        disabled={disabled}
        activeOpacity={0.7}
      >
        {subject.icon && (
          <View style={styles.iconContainer}>
            <Text style={styles.icon}>{subject.icon}</Text>
          </View>
        )}

        <View style={styles.info}>
          <Text style={[styles.name, disabled && styles.disabledText]}>
            {subject.name}
          </Text>
          {subject.description && (
            <Text style={styles.description}>{subject.description}</Text>
          )}
        </View>

        <View
          style={[
            styles.toggle,
            subject.enabled && styles.toggleActive,
            disabled && styles.toggleDisabled,
          ]}
        >
          <View
            style={[
              styles.toggleThumb,
              subject.enabled && styles.toggleThumbActive,
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
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
  },
  iconContainer: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#E8F4F8',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 16,
  },
  icon: {
    fontSize: 24,
  },
  info: {
    flex: 1,
  },
  name: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333333',
    marginBottom: 4,
  },
  description: {
    fontSize: 14,
    color: '#999999',
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
