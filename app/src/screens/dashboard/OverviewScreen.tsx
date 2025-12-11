/**
 * OverviewScreen
 * Main dashboard showing child learning progress overview
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  TouchableOpacity,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ChildSelector } from '../../components/dashboard/ChildSelector';
import { ProgressChart } from '../../components/dashboard/ProgressChart';
import { ActivityItem } from '../../components/dashboard/ActivityItem';
import { Card } from '../../components/common/Card';
import { ChildProfile, LearningActivity, DataPoint } from '../../types';

interface TodayStats {
  sessionsToday: number;
  minutesToday: number;
  questionsToday: number;
  streakDays: number;
}

export const OverviewScreen: React.FC = () => {
  const [refreshing, setRefreshing] = useState(false);
  const [selectedChild, setSelectedChild] = useState<ChildProfile | null>(null);
  const [children, setChildren] = useState<ChildProfile[]>([]);
  const [todayStats, setTodayStats] = useState<TodayStats | null>(null);
  const [weeklyProgress, setWeeklyProgress] = useState<DataPoint[]>([]);
  const [recentActivities, setRecentActivities] = useState<LearningActivity[]>([]);

  useEffect(() => {
    loadData();
  }, [selectedChild]);

  const loadData = async () => {
    // TODO: Replace with actual API calls
    // Mock data for demonstration
    setChildren([
      {
        id: '1',
        parentId: 'parent1',
        name: 'Emma',
        age: 10,
        dateOfBirth: '2014-05-15',
        grade: '5',
        school: 'Lincoln Elementary',
        learningGoals: [],
        preferences: {
          tutorVoice: 'female',
          tutorSpeed: 1.0,
          difficultyLevel: 'adaptive',
          subjects: ['Math', 'Reading', 'Science'],
          dailyLearningTimeLimit: 120,
          screenTimeBreakInterval: 30,
          restrictedApps: [],
        },
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
      {
        id: '2',
        parentId: 'parent1',
        name: 'Lucas',
        age: 8,
        dateOfBirth: '2016-08-22',
        grade: '3',
        school: 'Lincoln Elementary',
        learningGoals: [],
        preferences: {
          tutorVoice: 'male',
          tutorSpeed: 1.0,
          difficultyLevel: 'adaptive',
          subjects: ['Math', 'Reading'],
          dailyLearningTimeLimit: 90,
          screenTimeBreakInterval: 25,
          restrictedApps: [],
        },
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
    ]);

    if (!selectedChild && children.length > 0) {
      setSelectedChild(children[0]);
    }

    setTodayStats({
      sessionsToday: 3,
      minutesToday: 47,
      questionsToday: 15,
      streakDays: 7,
    });

    const today = new Date();
    setWeeklyProgress([
      { date: new Date(today.getTime() - 6 * 86400000).toISOString(), value: 25 },
      { date: new Date(today.getTime() - 5 * 86400000).toISOString(), value: 35 },
      { date: new Date(today.getTime() - 4 * 86400000).toISOString(), value: 40 },
      { date: new Date(today.getTime() - 3 * 86400000).toISOString(), value: 30 },
      { date: new Date(today.getTime() - 2 * 86400000).toISOString(), value: 50 },
      { date: new Date(today.getTime() - 1 * 86400000).toISOString(), value: 45 },
      { date: today.toISOString(), value: 47 },
    ]);

    setRecentActivities([
      {
        id: '1',
        sessionId: 's1',
        type: 'tutoring',
        subject: 'Math',
        topic: 'Multiplication',
        startTime: new Date(Date.now() - 1800000).toISOString(),
        duration: 900,
        questionsAsked: 8,
        answersProvided: 8,
        confidence: 85,
        engagement: 90,
        metadata: {},
      },
      {
        id: '2',
        sessionId: 's1',
        type: 'reading',
        subject: 'Reading',
        topic: 'Comprehension',
        startTime: new Date(Date.now() - 7200000).toISOString(),
        duration: 1200,
        questionsAsked: 5,
        answersProvided: 5,
        confidence: 78,
        engagement: 82,
        metadata: {},
      },
      {
        id: '3',
        sessionId: 's2',
        type: 'exploration',
        subject: 'Science',
        topic: 'Solar System',
        startTime: new Date(Date.now() - 86400000).toISOString(),
        duration: 600,
        questionsAsked: 12,
        answersProvided: 12,
        confidence: 92,
        engagement: 95,
        metadata: {},
      },
    ]);
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  const handleChildSelect = (child: ChildProfile) => {
    setSelectedChild(child);
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.greeting}>Welcome back!</Text>
          <Text style={styles.subtitle}>Here's how your child is learning</Text>
        </View>

        {/* Child Selector */}
        <ChildSelector
          children={children}
          selectedChild={selectedChild}
          onSelectChild={handleChildSelect}
          style={styles.childSelector}
        />

        {/* Today's Activity Summary */}
        {todayStats && (
          <Card style={styles.summaryCard}>
            <View style={styles.summaryHeader}>
              <Text style={styles.sectionTitle}>Today's Activity</Text>
              <Text style={styles.date}>
                {new Date().toLocaleDateString('en-US', {
                  month: 'short',
                  day: 'numeric',
                })}
              </Text>
            </View>
            <View style={styles.statsGrid}>
              <StatBox
                icon="📚"
                value={todayStats.sessionsToday.toString()}
                label="Sessions"
                color="#2196F3"
              />
              <StatBox
                icon="⏱️"
                value={`${todayStats.minutesToday}`}
                label="Minutes"
                color="#4CAF50"
              />
              <StatBox
                icon="❓"
                value={todayStats.questionsToday.toString()}
                label="Questions"
                color="#FF9800"
              />
              <StatBox
                icon="🔥"
                value={`${todayStats.streakDays}`}
                label="Day Streak"
                color="#F44336"
              />
            </View>
          </Card>
        )}

        {/* Weekly Progress Chart */}
        <Card style={styles.chartCard}>
          <ProgressChart
            data={weeklyProgress}
            title="Weekly Learning Time (minutes)"
            color="#4A90A4"
            height={200}
          />
        </Card>

        {/* Quick Actions */}
        <View style={styles.quickActions}>
          <Text style={styles.sectionTitle}>Quick Actions</Text>
          <View style={styles.actionButtons}>
            <ActionButton icon="📊" label="View Progress" color="#2196F3" />
            <ActionButton icon="📋" label="Activity Log" color="#4CAF50" />
            <ActionButton icon="🏆" label="Achievements" color="#FFC107" />
            <ActionButton icon="⚙️" label="Settings" color="#9E9E9E" />
          </View>
        </View>

        {/* Recent Sessions */}
        <View style={styles.recentSection}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Recent Sessions</Text>
            <TouchableOpacity>
              <Text style={styles.viewAllText}>View All</Text>
            </TouchableOpacity>
          </View>
          {recentActivities.map((activity) => (
            <ActivityItem
              key={activity.id}
              activity={activity}
              onPress={() => console.log('Activity pressed:', activity.id)}
            />
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

const StatBox: React.FC<{
  icon: string;
  value: string;
  label: string;
  color: string;
}> = ({ icon, value, label, color }) => (
  <View style={styles.statBox}>
    <Text style={styles.statIcon}>{icon}</Text>
    <Text style={[styles.statValue, { color }]}>{value}</Text>
    <Text style={styles.statLabel}>{label}</Text>
  </View>
);

const ActionButton: React.FC<{
  icon: string;
  label: string;
  color: string;
}> = ({ icon, label, color }) => (
  <TouchableOpacity style={styles.actionButton} activeOpacity={0.7}>
    <View style={[styles.actionIcon, { backgroundColor: `${color}20` }]}>
      <Text style={styles.actionIconText}>{icon}</Text>
    </View>
    <Text style={styles.actionLabel} numberOfLines={2}>
      {label}
    </Text>
  </TouchableOpacity>
);

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F7FA',
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 32,
  },
  header: {
    marginBottom: 20,
  },
  greeting: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#333333',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 15,
    color: '#666666',
  },
  childSelector: {
    marginBottom: 16,
  },
  summaryCard: {
    marginBottom: 16,
  },
  summaryHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333333',
  },
  date: {
    fontSize: 13,
    color: '#999999',
  },
  statsGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 8,
  },
  statBox: {
    flex: 1,
    alignItems: 'center',
    padding: 12,
    backgroundColor: '#F9FAFB',
    borderRadius: 12,
  },
  statIcon: {
    fontSize: 24,
    marginBottom: 8,
  },
  statValue: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 11,
    color: '#666666',
    textAlign: 'center',
  },
  chartCard: {
    marginBottom: 16,
  },
  quickActions: {
    marginBottom: 20,
  },
  actionButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 12,
    gap: 8,
  },
  actionButton: {
    flex: 1,
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 2,
  },
  actionIcon: {
    width: 48,
    height: 48,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  actionIconText: {
    fontSize: 24,
  },
  actionLabel: {
    fontSize: 11,
    fontWeight: '500',
    color: '#333333',
    textAlign: 'center',
  },
  recentSection: {
    marginBottom: 16,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  viewAllText: {
    fontSize: 13,
    color: '#4A90A4',
    fontWeight: '600',
  },
});
