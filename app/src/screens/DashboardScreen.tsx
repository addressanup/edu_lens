/**
 * Dashboard Screen - Main overview of child's learning progress
 */

import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  TouchableOpacity,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '../auth/AuthContext';
import { useBluetooth } from '../bluetooth/BluetoothContext';

interface LearningStats {
  totalSessions: number;
  totalMinutes: number;
  problemsSolved: number;
  streakDays: number;
  subjectBreakdown: {
    math: number;
    reading: number;
    science: number;
    socialStudies: number;
  };
  recentActivity: ActivityItem[];
}

interface ActivityItem {
  id: string;
  timestamp: Date;
  type: 'problem_solved' | 'session_completed' | 'milestone_reached';
  subject: string;
  description: string;
}

export function DashboardScreen(): React.JSX.Element {
  const { user } = useAuth();
  const { connectedDevice, requestBatteryLevel } = useBluetooth();
  const [stats, setStats] = useState<LearningStats | null>(null);
  const [batteryLevel, setBatteryLevel] = useState<number | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadDashboardData();
  }, []);

  useEffect(() => {
    if (connectedDevice) {
      loadBatteryLevel();
    }
  }, [connectedDevice]);

  const loadDashboardData = async () => {
    // TODO: Fetch actual data from API
    setStats({
      totalSessions: 47,
      totalMinutes: 892,
      problemsSolved: 234,
      streakDays: 5,
      subjectBreakdown: {
        math: 45,
        reading: 30,
        science: 15,
        socialStudies: 10,
      },
      recentActivity: [
        {
          id: '1',
          timestamp: new Date(),
          type: 'problem_solved',
          subject: 'Math',
          description: 'Completed 5 multiplication problems',
        },
        {
          id: '2',
          timestamp: new Date(Date.now() - 3600000),
          type: 'session_completed',
          subject: 'Reading',
          description: '15 minute reading comprehension session',
        },
      ],
    });
  };

  const loadBatteryLevel = async () => {
    try {
      const level = await requestBatteryLevel();
      setBatteryLevel(level);
    } catch (error) {
      console.error('Failed to get battery level:', error);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadDashboardData();
    if (connectedDevice) {
      await loadBatteryLevel();
    }
    setRefreshing(false);
  };

  const childName = user?.children[0]?.name || 'Your Child';

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.greeting}>Hello!</Text>
          <Text style={styles.childName}>{childName}'s Progress</Text>
        </View>

        {/* Device Status */}
        <View style={styles.deviceCard}>
          <View style={styles.deviceStatus}>
            <View
              style={[
                styles.statusDot,
                { backgroundColor: connectedDevice ? '#4CAF50' : '#9E9E9E' },
              ]}
            />
            <Text style={styles.deviceText}>
              {connectedDevice
                ? `EduLens Connected`
                : 'EduLens Not Connected'}
            </Text>
          </View>
          {batteryLevel !== null && (
            <Text style={styles.batteryText}>Battery: {batteryLevel}%</Text>
          )}
        </View>

        {/* Stats Overview */}
        {stats && (
          <>
            <View style={styles.statsGrid}>
              <StatCard
                title="Sessions"
                value={stats.totalSessions.toString()}
                subtitle="this week"
              />
              <StatCard
                title="Time Learning"
                value={`${Math.floor(stats.totalMinutes / 60)}h`}
                subtitle={`${stats.totalMinutes % 60}m total`}
              />
              <StatCard
                title="Problems"
                value={stats.problemsSolved.toString()}
                subtitle="solved"
              />
              <StatCard
                title="Streak"
                value={`${stats.streakDays}`}
                subtitle="days"
              />
            </View>

            {/* Subject Breakdown */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Subject Focus</Text>
              <View style={styles.subjectBar}>
                <View
                  style={[
                    styles.subjectSegment,
                    { flex: stats.subjectBreakdown.math, backgroundColor: '#2196F3' },
                  ]}
                />
                <View
                  style={[
                    styles.subjectSegment,
                    { flex: stats.subjectBreakdown.reading, backgroundColor: '#4CAF50' },
                  ]}
                />
                <View
                  style={[
                    styles.subjectSegment,
                    { flex: stats.subjectBreakdown.science, backgroundColor: '#FF9800' },
                  ]}
                />
                <View
                  style={[
                    styles.subjectSegment,
                    { flex: stats.subjectBreakdown.socialStudies, backgroundColor: '#9C27B0' },
                  ]}
                />
              </View>
              <View style={styles.legend}>
                <LegendItem color="#2196F3" label="Math" />
                <LegendItem color="#4CAF50" label="Reading" />
                <LegendItem color="#FF9800" label="Science" />
                <LegendItem color="#9C27B0" label="Social Studies" />
              </View>
            </View>

            {/* Recent Activity */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Recent Activity</Text>
              {stats.recentActivity.map((activity) => (
                <View key={activity.id} style={styles.activityItem}>
                  <View style={styles.activityIcon}>
                    <Text style={styles.activityIconText}>
                      {activity.type === 'problem_solved' ? '✓' : '★'}
                    </Text>
                  </View>
                  <View style={styles.activityContent}>
                    <Text style={styles.activitySubject}>{activity.subject}</Text>
                    <Text style={styles.activityDescription}>
                      {activity.description}
                    </Text>
                  </View>
                </View>
              ))}
            </View>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function StatCard({
  title,
  value,
  subtitle,
}: {
  title: string;
  value: string;
  subtitle: string;
}) {
  return (
    <View style={styles.statCard}>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statTitle}>{title}</Text>
      <Text style={styles.statSubtitle}>{subtitle}</Text>
    </View>
  );
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <View style={styles.legendItem}>
      <View style={[styles.legendDot, { backgroundColor: color }]} />
      <Text style={styles.legendText}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  scrollContent: {
    padding: 16,
  },
  header: {
    marginBottom: 20,
  },
  greeting: {
    fontSize: 16,
    color: '#666',
  },
  childName: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#333',
  },
  deviceCard: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  deviceStatus: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statusDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: 8,
  },
  deviceText: {
    fontSize: 14,
    color: '#333',
  },
  batteryText: {
    fontSize: 14,
    color: '#666',
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginHorizontal: -6,
    marginBottom: 20,
  },
  statCard: {
    width: '50%',
    padding: 6,
  },
  statValue: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#2196F3',
  },
  statTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  statSubtitle: {
    fontSize: 12,
    color: '#666',
  },
  section: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 12,
  },
  subjectBar: {
    flexDirection: 'row',
    height: 24,
    borderRadius: 12,
    overflow: 'hidden',
  },
  subjectSegment: {
    height: '100%',
  },
  legend: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 12,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 16,
    marginTop: 4,
  },
  legendDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 4,
  },
  legendText: {
    fontSize: 12,
    color: '#666',
  },
  activityItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#EEE',
  },
  activityIcon: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#E3F2FD',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  activityIconText: {
    fontSize: 16,
  },
  activityContent: {
    flex: 1,
  },
  activitySubject: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  activityDescription: {
    fontSize: 13,
    color: '#666',
  },
});
