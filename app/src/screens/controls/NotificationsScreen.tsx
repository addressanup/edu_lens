/**
 * NotificationsScreen
 * Screen for managing notification preferences
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
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { useAuthStore } from '../../store';

interface NotificationSettings {
  sessionStartEnd: boolean;
  progressMilestones: boolean;
  weeklyReports: boolean;
  dailySummary: boolean;
  achievements: boolean;
  deviceAlerts: boolean;
  safetyAlerts: boolean;
  lowBattery: boolean;
  quietHoursEnabled: boolean;
  quietHoursStart: { hour: number; minute: number };
  quietHoursEnd: { hour: number; minute: number };
  emailNotifications: boolean;
  pushNotifications: boolean;
  smsNotifications: boolean;
}

export const NotificationsScreen: React.FC = () => {
  const navigation = useNavigation();
  const user = useAuthStore((state) => state.user);

  const [settings, setSettings] = useState<NotificationSettings>({
    sessionStartEnd: true,
    progressMilestones: true,
    weeklyReports: true,
    dailySummary: false,
    achievements: true,
    deviceAlerts: true,
    safetyAlerts: true,
    lowBattery: true,
    quietHoursEnabled: false,
    quietHoursStart: { hour: 22, minute: 0 },
    quietHoursEnd: { hour: 7, minute: 0 },
    emailNotifications: true,
    pushNotifications: true,
    smsNotifications: false,
  });

  const [hasChanges, setHasChanges] = useState(false);

  // Load user preferences
  useEffect(() => {
    if (user?.preferences) {
      setSettings((prev) => ({
        ...prev,
        emailNotifications: user.preferences.emailNotifications,
        pushNotifications: user.preferences.pushNotifications,
        weeklyReports: user.preferences.weeklyReports,
      }));
    }
  }, [user]);

  const handleToggle = (key: keyof NotificationSettings) => {
    setSettings((prev) => ({
      ...prev,
      [key]: !prev[key as keyof typeof prev],
    }));
    setHasChanges(true);
  };

  const handleSave = async () => {
    // TODO: Implement API call to save notification settings
    Alert.alert('Success', 'Notification settings updated successfully');
    setHasChanges(false);
  };

  const handleTestNotification = () => {
    Alert.alert(
      'Test Notification',
      'A test notification will be sent to all enabled channels',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Send',
          onPress: () => {
            Alert.alert('Sent', 'Test notification sent!');
          },
        },
      ]
    );
  };

  const formatTime = (hour: number, minute: number): string => {
    const period = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
    const displayMinute = minute.toString().padStart(2, '0');
    return `${displayHour}:${displayMinute} ${period}`;
  };

  const renderToggleRow = (
    title: string,
    description: string,
    key: keyof NotificationSettings,
    critical: boolean = false
  ) => (
    <TouchableOpacity
      style={styles.toggleRow}
      onPress={() => handleToggle(key)}
    >
      <View style={styles.toggleInfo}>
        <View style={styles.toggleHeader}>
          <Text style={styles.toggleTitle}>{title}</Text>
          {critical && (
            <View style={styles.criticalBadge}>
              <Text style={styles.criticalText}>Important</Text>
            </View>
          )}
        </View>
        <Text style={styles.toggleDescription}>{description}</Text>
      </View>
      <View
        style={[
          styles.toggle,
          settings[key] && styles.toggleActive,
        ]}
      >
        <View
          style={[
            styles.toggleThumb,
            settings[key] && styles.toggleThumbActive,
          ]}
        />
      </View>
    </TouchableOpacity>
  );

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
          <Text style={styles.title}>Notifications</Text>
          <Text style={styles.subtitle}>
            Manage your notification preferences
          </Text>
        </View>

        {/* Notification Channels */}
        <Card style={styles.card}>
          <Text style={styles.cardTitle}>Notification Channels</Text>
          <Text style={styles.cardDescription}>
            Choose how you want to receive notifications
          </Text>

          {renderToggleRow(
            'Push Notifications',
            'Receive instant alerts on your device',
            'pushNotifications'
          )}

          <View style={styles.divider} />

          {renderToggleRow(
            'Email Notifications',
            'Get updates via email',
            'emailNotifications'
          )}

          <View style={styles.divider} />

          {renderToggleRow(
            'SMS Notifications',
            'Receive text messages for critical alerts',
            'smsNotifications'
          )}
        </Card>

        {/* Learning Activity Alerts */}
        <Card style={styles.card}>
          <Text style={styles.cardTitle}>Learning Activity</Text>
          <Text style={styles.cardDescription}>
            Get notified about your child's learning sessions
          </Text>

          {renderToggleRow(
            'Session Start/End',
            'Alert when learning session begins or ends',
            'sessionStartEnd'
          )}

          <View style={styles.divider} />

          {renderToggleRow(
            'Progress Milestones',
            'Celebrate when your child reaches goals',
            'progressMilestones'
          )}

          <View style={styles.divider} />

          {renderToggleRow(
            'Achievements',
            'New badges and achievements earned',
            'achievements'
          )}

          <View style={styles.divider} />

          {renderToggleRow(
            'Daily Summary',
            'End-of-day learning summary',
            'dailySummary'
          )}
        </Card>

        {/* Reports */}
        <Card style={styles.card}>
          <Text style={styles.cardTitle}>Reports</Text>
          <Text style={styles.cardDescription}>
            Regular progress reports and insights
          </Text>

          {renderToggleRow(
            'Weekly Reports',
            'Comprehensive weekly learning summary',
            'weeklyReports'
          )}

          <View style={styles.infoBox}>
            <Text style={styles.infoText}>
              📊 Weekly reports are sent every Sunday evening
            </Text>
          </View>
        </Card>

        {/* Device & Safety Alerts */}
        <Card style={styles.card}>
          <Text style={styles.cardTitle}>Device & Safety</Text>
          <Text style={styles.cardDescription}>
            Important device and safety notifications
          </Text>

          {renderToggleRow(
            'Device Alerts',
            'Connection issues and device updates',
            'deviceAlerts',
            true
          )}

          <View style={styles.divider} />

          {renderToggleRow(
            'Safety Alerts',
            'Critical safety and security notifications',
            'safetyAlerts',
            true
          )}

          <View style={styles.divider} />

          {renderToggleRow(
            'Low Battery',
            'Alert when device battery is low',
            'lowBattery'
          )}
        </Card>

        {/* Quiet Hours */}
        <Card style={styles.card}>
          <Text style={styles.cardTitle}>Quiet Hours</Text>
          <Text style={styles.cardDescription}>
            Pause non-critical notifications during specific hours
          </Text>

          {renderToggleRow(
            'Enable Quiet Hours',
            'Mute notifications during quiet hours',
            'quietHoursEnabled'
          )}

          {settings.quietHoursEnabled && (
            <>
              <View style={styles.divider} />

              <View style={styles.quietHoursSettings}>
                <TouchableOpacity style={styles.timeSelector}>
                  <Text style={styles.timeLabel}>Start Time</Text>
                  <Text style={styles.timeValue}>
                    {formatTime(
                      settings.quietHoursStart.hour,
                      settings.quietHoursStart.minute
                    )}
                  </Text>
                </TouchableOpacity>

                <View style={styles.timeSeparator}>
                  <Text style={styles.timeSeparatorText}>to</Text>
                </View>

                <TouchableOpacity style={styles.timeSelector}>
                  <Text style={styles.timeLabel}>End Time</Text>
                  <Text style={styles.timeValue}>
                    {formatTime(
                      settings.quietHoursEnd.hour,
                      settings.quietHoursEnd.minute
                    )}
                  </Text>
                </TouchableOpacity>
              </View>

              <View style={styles.infoBox}>
                <Text style={styles.infoText}>
                  ⚠️ Safety and critical alerts will still be delivered during quiet
                  hours
                </Text>
              </View>
            </>
          )}
        </Card>

        {/* Test Notifications */}
        <Card style={styles.card}>
          <Text style={styles.cardTitle}>Test Notifications</Text>
          <Text style={styles.cardDescription}>
            Send a test notification to verify your settings
          </Text>

          <Button
            title="Send Test Notification"
            onPress={handleTestNotification}
            variant="outline"
            style={styles.testButton}
          />
        </Card>

        {/* Actions */}
        <View style={styles.actions}>
          <Button
            title="Save Changes"
            onPress={handleSave}
            disabled={!hasChanges}
            style={styles.saveButton}
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
    marginBottom: 16,
  },
  toggleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
  },
  toggleInfo: {
    flex: 1,
    marginRight: 16,
  },
  toggleHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  toggleTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333333',
    flex: 1,
  },
  toggleDescription: {
    fontSize: 14,
    color: '#999999',
  },
  criticalBadge: {
    backgroundColor: '#FFE8E8',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
    marginLeft: 8,
  },
  criticalText: {
    fontSize: 10,
    fontWeight: '600',
    color: '#FF5252',
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
  toggleThumb: {
    width: 27,
    height: 27,
    borderRadius: 13.5,
    backgroundColor: '#FFFFFF',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 2,
    elevation: 2,
  },
  toggleThumbActive: {
    alignSelf: 'flex-end',
  },
  divider: {
    height: 1,
    backgroundColor: '#F0F0F0',
    marginVertical: 16,
  },
  quietHoursSettings: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 16,
    marginBottom: 16,
  },
  timeSelector: {
    flex: 1,
    backgroundColor: '#F8FAFB',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  timeLabel: {
    fontSize: 12,
    color: '#999999',
    marginBottom: 4,
  },
  timeValue: {
    fontSize: 18,
    fontWeight: '700',
    color: '#333333',
  },
  timeSeparator: {
    paddingHorizontal: 12,
  },
  timeSeparatorText: {
    fontSize: 14,
    color: '#999999',
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
  testButton: {
    marginTop: 12,
  },
  actions: {
    marginTop: 24,
  },
  saveButton: {
    width: '100%',
  },
  bottomPadding: {
    height: 40,
  },
});
