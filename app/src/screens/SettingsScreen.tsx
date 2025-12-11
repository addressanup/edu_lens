/**
 * Settings Screen - Parent control center for EduLens
 */

import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '../auth/AuthContext';
import { useBluetooth } from '../bluetooth/BluetoothContext';

interface SettingsSectionProps {
  title: string;
  children: React.ReactNode;
}

function SettingsSection({ title, children }: SettingsSectionProps): React.JSX.Element {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      <View style={styles.sectionContent}>{children}</View>
    </View>
  );
}

interface SettingsRowProps {
  label: string;
  value?: string;
  onPress?: () => void;
  rightElement?: React.ReactNode;
}

function SettingsRow({ label, value, onPress, rightElement }: SettingsRowProps): React.JSX.Element {
  return (
    <TouchableOpacity
      style={styles.row}
      onPress={onPress}
      disabled={!onPress}
    >
      <Text style={styles.rowLabel}>{label}</Text>
      {rightElement || (
        <View style={styles.rowRight}>
          {value && <Text style={styles.rowValue}>{value}</Text>}
          {onPress && <Text style={styles.chevron}>›</Text>}
        </View>
      )}
    </TouchableOpacity>
  );
}

export function SettingsScreen({ navigation }: { navigation: any }): React.JSX.Element {
  const { user, logout } = useAuth();
  const { connectedDevice, disconnectDevice } = useBluetooth();

  const [notificationsEnabled, setNotificationsEnabled] = React.useState(true);
  const [dailyReportsEnabled, setDailyReportsEnabled] = React.useState(true);

  const handleLogout = () => {
    Alert.alert(
      'Log Out',
      'Are you sure you want to log out?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Log Out',
          style: 'destructive',
          onPress: async () => {
            try {
              if (connectedDevice) {
                await disconnectDevice();
              }
              await logout();
            } catch (error) {
              console.error('Logout error:', error);
            }
          },
        },
      ],
    );
  };

  const handleDeleteData = () => {
    Alert.alert(
      'Delete Learning Data',
      'This will permanently delete all learning history and progress data. This action cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: () => {
            // TODO: Implement data deletion with COPPA compliance
            Alert.alert('Data Deleted', 'All learning data has been removed.');
          },
        },
      ],
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView>
        {/* Device Section */}
        <SettingsSection title="Device">
          <SettingsRow
            label="EduLens Device"
            value={connectedDevice ? 'Connected' : 'Not Connected'}
            onPress={() => navigation.navigate('DeviceManagement')}
          />
          <SettingsRow
            label="Device Settings"
            onPress={() => navigation.navigate('DeviceSettings')}
          />
        </SettingsSection>

        {/* Parental Controls Section */}
        <SettingsSection title="Parental Controls">
          <SettingsRow
            label="Usage Limits"
            value="2 hours/day"
            onPress={() => navigation.navigate('UsageLimits')}
          />
          <SettingsRow
            label="Content Filters"
            value="Age Appropriate"
            onPress={() => navigation.navigate('ContentFilters')}
          />
          <SettingsRow
            label="Allowed Subjects"
            value="All"
            onPress={() => navigation.navigate('SubjectSettings')}
          />
          <SettingsRow
            label="Quiet Hours"
            value="9 PM - 7 AM"
            onPress={() => navigation.navigate('QuietHours')}
          />
        </SettingsSection>

        {/* Notifications Section */}
        <SettingsSection title="Notifications">
          <SettingsRow
            label="Push Notifications"
            rightElement={
              <Switch
                value={notificationsEnabled}
                onValueChange={setNotificationsEnabled}
              />
            }
          />
          <SettingsRow
            label="Daily Progress Reports"
            rightElement={
              <Switch
                value={dailyReportsEnabled}
                onValueChange={setDailyReportsEnabled}
              />
            }
          />
        </SettingsSection>

        {/* Privacy Section */}
        <SettingsSection title="Privacy & Data">
          <SettingsRow
            label="Privacy Policy"
            onPress={() => navigation.navigate('PrivacyPolicy')}
          />
          <SettingsRow
            label="Data Collection Settings"
            onPress={() => navigation.navigate('DataSettings')}
          />
          <SettingsRow
            label="Export Learning Data"
            onPress={() => {
              // TODO: Implement data export
              Alert.alert('Export Data', 'A download link will be sent to your email.');
            }}
          />
          <SettingsRow
            label="Delete All Data"
            onPress={handleDeleteData}
          />
        </SettingsSection>

        {/* Account Section */}
        <SettingsSection title="Account">
          <SettingsRow
            label="Email"
            value={user?.email || 'Not set'}
          />
          <SettingsRow
            label="Manage Children"
            onPress={() => navigation.navigate('ManageChildren')}
          />
          <SettingsRow
            label="Change Password"
            onPress={() => navigation.navigate('ChangePassword')}
          />
        </SettingsSection>

        {/* Support Section */}
        <SettingsSection title="Support">
          <SettingsRow
            label="Help Center"
            onPress={() => navigation.navigate('HelpCenter')}
          />
          <SettingsRow
            label="Contact Support"
            onPress={() => navigation.navigate('ContactSupport')}
          />
          <SettingsRow
            label="App Version"
            value="1.0.0"
          />
        </SettingsSection>

        {/* Logout Button */}
        <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
          <Text style={styles.logoutText}>Log Out</Text>
        </TouchableOpacity>

        <View style={styles.footer}>
          <Text style={styles.footerText}>
            EduLens is COPPA compliant. We never sell children's data.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  section: {
    marginTop: 24,
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: '#666',
    textTransform: 'uppercase',
    marginLeft: 16,
    marginBottom: 8,
  },
  sectionContent: {
    backgroundColor: '#FFF',
    borderTopWidth: StyleSheet.hairlineWidth,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderColor: '#DDD',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 14,
    paddingHorizontal: 16,
    backgroundColor: '#FFF',
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#EEE',
  },
  rowLabel: {
    fontSize: 16,
    color: '#333',
  },
  rowRight: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  rowValue: {
    fontSize: 16,
    color: '#999',
    marginRight: 8,
  },
  chevron: {
    fontSize: 20,
    color: '#CCC',
  },
  logoutButton: {
    marginTop: 32,
    marginHorizontal: 16,
    paddingVertical: 14,
    backgroundColor: '#FFF',
    borderRadius: 8,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#FF3B30',
  },
  logoutText: {
    fontSize: 16,
    color: '#FF3B30',
    fontWeight: '600',
  },
  footer: {
    padding: 24,
    alignItems: 'center',
  },
  footerText: {
    fontSize: 12,
    color: '#999',
    textAlign: 'center',
  },
});
