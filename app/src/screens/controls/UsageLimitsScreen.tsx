/**
 * UsageLimitsScreen
 * Screen for managing child usage time limits and schedules
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  SafeAreaView,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { TimeSlider } from '../../components/controls/TimeSlider';
import { SchedulePicker, WeeklySchedule } from '../../components/controls/SchedulePicker';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { useChild } from '../../hooks/useChild';

interface UsageLimits {
  dailyLimit: number; // minutes
  weekdayLimit: number; // minutes
  weekendLimit: number; // minutes
  breakReminderInterval: number; // minutes
  schedule: WeeklySchedule;
}

const DEFAULT_SCHEDULE: WeeklySchedule = {
  monday: [{ startHour: 9, startMinute: 0, endHour: 17, endMinute: 0 }],
  tuesday: [{ startHour: 9, startMinute: 0, endHour: 17, endMinute: 0 }],
  wednesday: [{ startHour: 9, startMinute: 0, endHour: 17, endMinute: 0 }],
  thursday: [{ startHour: 9, startMinute: 0, endHour: 17, endMinute: 0 }],
  friday: [{ startHour: 9, startMinute: 0, endHour: 17, endMinute: 0 }],
  saturday: [{ startHour: 9, startMinute: 0, endHour: 21, endMinute: 0 }],
  sunday: [{ startHour: 9, startMinute: 0, endHour: 21, endMinute: 0 }],
};

export const UsageLimitsScreen: React.FC = () => {
  const navigation = useNavigation();
  const { activeChild, updatePreferences, isLoading } = useChild();

  const [limits, setLimits] = useState<UsageLimits>({
    dailyLimit: 120, // 2 hours default
    weekdayLimit: 90, // 1.5 hours on weekdays
    weekendLimit: 150, // 2.5 hours on weekends
    breakReminderInterval: 30, // 30 min breaks
    schedule: DEFAULT_SCHEDULE,
  });

  const [hasChanges, setHasChanges] = useState(false);

  // Load current child's preferences
  useEffect(() => {
    if (activeChild?.preferences) {
      setLimits({
        dailyLimit: activeChild.preferences.dailyLearningTimeLimit || 120,
        weekdayLimit: activeChild.preferences.dailyLearningTimeLimit || 90,
        weekendLimit: activeChild.preferences.dailyLearningTimeLimit || 150,
        breakReminderInterval: activeChild.preferences.screenTimeBreakInterval || 30,
        schedule: DEFAULT_SCHEDULE,
      });
    }
  }, [activeChild]);

  const handleLimitChange = (key: keyof UsageLimits, value: any) => {
    setLimits((prev) => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  const handleSave = async () => {
    if (!activeChild) {
      Alert.alert('Error', 'No active child selected');
      return;
    }

    const success = await updatePreferences(activeChild.id, {
      dailyLearningTimeLimit: limits.dailyLimit,
      screenTimeBreakInterval: limits.breakReminderInterval,
    });

    if (success) {
      Alert.alert('Success', 'Usage limits updated successfully');
      setHasChanges(false);
    } else {
      Alert.alert('Error', 'Failed to update usage limits');
    }
  };

  const handleReset = () => {
    Alert.alert(
      'Reset Limits',
      'Are you sure you want to reset all limits to defaults?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Reset',
          style: 'destructive',
          onPress: () => {
            setLimits({
              dailyLimit: 120,
              weekdayLimit: 90,
              weekendLimit: 150,
              breakReminderInterval: 30,
              schedule: DEFAULT_SCHEDULE,
            });
            setHasChanges(true);
          },
        },
      ]
    );
  };

  if (!activeChild) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.emptyState}>
          <Text style={styles.emptyText}>No child selected</Text>
          <Text style={styles.emptySubtext}>
            Please select a child from the dashboard
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.scrollView} contentContainerStyle={styles.content}>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity
            onPress={() => navigation.goBack()}
            style={styles.backButton}
          >
            <Text style={styles.backText}>‹ Back</Text>
          </TouchableOpacity>
          <Text style={styles.title}>Usage Limits</Text>
          <Text style={styles.subtitle}>
            Set time limits for {activeChild.name}
          </Text>
        </View>

        {/* Daily Limits Card */}
        <Card style={styles.card}>
          <Text style={styles.cardTitle}>Daily Time Limits</Text>
          <Text style={styles.cardDescription}>
            Set maximum screen time per day
          </Text>

          <TimeSlider
            label="Daily Limit"
            value={limits.dailyLimit}
            onChange={(value) => handleLimitChange('dailyLimit', value)}
            min={0}
            max={480}
            step={15}
          />

          <View style={styles.divider} />

          <TimeSlider
            label="Weekday Limit"
            value={limits.weekdayLimit}
            onChange={(value) => handleLimitChange('weekdayLimit', value)}
            min={0}
            max={480}
            step={15}
          />

          <View style={styles.divider} />

          <TimeSlider
            label="Weekend Limit"
            value={limits.weekendLimit}
            onChange={(value) => handleLimitChange('weekendLimit', value)}
            min={0}
            max={480}
            step={15}
          />
        </Card>

        {/* Break Reminders Card */}
        <Card style={styles.card}>
          <Text style={styles.cardTitle}>Break Reminders</Text>
          <Text style={styles.cardDescription}>
            Remind your child to take regular breaks
          </Text>

          <TimeSlider
            label="Reminder Interval"
            value={limits.breakReminderInterval}
            onChange={(value) => handleLimitChange('breakReminderInterval', value)}
            min={15}
            max={120}
            step={15}
          />

          <View style={styles.infoBox}>
            <Text style={styles.infoText}>
              💡 Regular breaks help prevent eye strain and maintain focus
            </Text>
          </View>
        </Card>

        {/* Schedule Card */}
        <Card style={styles.card}>
          <Text style={styles.cardTitle}>Weekly Schedule</Text>
          <Text style={styles.cardDescription}>
            Set allowed usage hours for each day
          </Text>

          <SchedulePicker
            schedule={limits.schedule}
            onChange={(value) => handleLimitChange('schedule', value)}
            style={styles.schedulePicker}
          />
        </Card>

        {/* Quick Presets */}
        <Card style={styles.card}>
          <Text style={styles.cardTitle}>Quick Presets</Text>
          <View style={styles.presets}>
            <TouchableOpacity
              style={styles.presetButton}
              onPress={() => {
                handleLimitChange('dailyLimit', 60);
                handleLimitChange('weekdayLimit', 45);
                handleLimitChange('weekendLimit', 75);
                setHasChanges(true);
              }}
            >
              <Text style={styles.presetTitle}>Minimal</Text>
              <Text style={styles.presetSubtitle}>1 hr/day</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.presetButton}
              onPress={() => {
                handleLimitChange('dailyLimit', 120);
                handleLimitChange('weekdayLimit', 90);
                handleLimitChange('weekendLimit', 150);
                setHasChanges(true);
              }}
            >
              <Text style={styles.presetTitle}>Balanced</Text>
              <Text style={styles.presetSubtitle}>2 hr/day</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.presetButton}
              onPress={() => {
                handleLimitChange('dailyLimit', 240);
                handleLimitChange('weekdayLimit', 180);
                handleLimitChange('weekendLimit', 300);
                setHasChanges(true);
              }}
            >
              <Text style={styles.presetTitle}>Extended</Text>
              <Text style={styles.presetSubtitle}>4 hr/day</Text>
            </TouchableOpacity>
          </View>
        </Card>

        {/* Actions */}
        <View style={styles.actions}>
          <Button
            title="Save Changes"
            onPress={handleSave}
            disabled={!hasChanges || isLoading}
            loading={isLoading}
            style={styles.saveButton}
          />

          <Button
            title="Reset to Defaults"
            onPress={handleReset}
            variant="outline"
            style={styles.resetButton}
          />
        </View>

        <View style={styles.bottomPadding} />
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F8FAFB',
  },
  scrollView: {
    flex: 1,
  },
  content: {
    padding: 20,
  },
  header: {
    marginBottom: 24,
  },
  backButton: {
    marginBottom: 12,
  },
  backText: {
    fontSize: 16,
    color: '#4A90A4',
    fontWeight: '600',
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: '#333333',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#666666',
  },
  card: {
    marginBottom: 16,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#333333',
    marginBottom: 6,
  },
  cardDescription: {
    fontSize: 14,
    color: '#666666',
    marginBottom: 20,
  },
  divider: {
    height: 1,
    backgroundColor: '#F0F0F0',
    marginVertical: 16,
  },
  infoBox: {
    backgroundColor: '#E8F4F8',
    padding: 12,
    borderRadius: 8,
    marginTop: 16,
  },
  infoText: {
    fontSize: 14,
    color: '#4A90A4',
    lineHeight: 20,
  },
  schedulePicker: {
    marginTop: 12,
  },
  presets: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 12,
  },
  presetButton: {
    flex: 1,
    backgroundColor: '#F8FAFB',
    padding: 16,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#E0E0E0',
    alignItems: 'center',
  },
  presetTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333333',
    marginBottom: 4,
  },
  presetSubtitle: {
    fontSize: 12,
    color: '#999999',
  },
  actions: {
    marginTop: 24,
    gap: 12,
  },
  saveButton: {
    width: '100%',
  },
  resetButton: {
    width: '100%',
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 40,
  },
  emptyText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333333',
    marginBottom: 8,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#999999',
    textAlign: 'center',
  },
  bottomPadding: {
    height: 40,
  },
});
