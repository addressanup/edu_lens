/**
 * ProgressScreen
 * Detailed progress view with subject breakdown and mastery levels
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
import { SubjectCard } from '../../components/dashboard/SubjectCard';
import { ProgressChart } from '../../components/dashboard/ProgressChart';
import { Card } from '../../components/common/Card';
import { SubjectProgress, DataPoint, ChildProfile } from '../../types';

type TimePeriod = 'week' | 'month' | 'year' | 'all';

interface ProgressData {
  subjectProgress: SubjectProgress[];
  confidenceTrend: DataPoint[];
  engagementTrend: DataPoint[];
  topStrengths: string[];
  areasForImprovement: string[];
  overallStats: {
    totalHours: number;
    averageConfidence: number;
    questionsAnswered: number;
    topicsExplored: number;
  };
}

export const ProgressScreen: React.FC = () => {
  const [refreshing, setRefreshing] = useState(false);
  const [selectedPeriod, setSelectedPeriod] = useState<TimePeriod>('week');
  const [progressData, setProgressData] = useState<ProgressData | null>(null);

  useEffect(() => {
    loadProgressData();
  }, [selectedPeriod]);

  const loadProgressData = async () => {
    // TODO: Replace with actual API call
    // Mock data for demonstration
    setProgressData({
      subjectProgress: [
        {
          subject: 'Math',
          duration: 2400, // 40 minutes
          questionsAsked: 45,
          confidenceLevel: 85,
          improvement: 12,
        },
        {
          subject: 'Reading',
          duration: 1800, // 30 minutes
          questionsAsked: 28,
          confidenceLevel: 92,
          improvement: 8,
        },
        {
          subject: 'Science',
          duration: 1200, // 20 minutes
          questionsAsked: 35,
          confidenceLevel: 78,
          improvement: 15,
        },
        {
          subject: 'Social Studies',
          duration: 900, // 15 minutes
          questionsAsked: 18,
          confidenceLevel: 68,
          improvement: -3,
        },
      ],
      confidenceTrend: generateTrendData(7, 70, 90),
      engagementTrend: generateTrendData(7, 75, 95),
      topStrengths: [
        'Reading Comprehension',
        'Basic Multiplication',
        'Scientific Method',
      ],
      areasForImprovement: [
        'Geography',
        'Long Division',
        'Paragraph Writing',
      ],
      overallStats: {
        totalHours: 18.5,
        averageConfidence: 81,
        questionsAnswered: 126,
        topicsExplored: 24,
      },
    });
  };

  const generateTrendData = (
    days: number,
    min: number,
    max: number
  ): DataPoint[] => {
    const data: DataPoint[] = [];
    const today = new Date();
    for (let i = days - 1; i >= 0; i--) {
      const date = new Date(today.getTime() - i * 86400000);
      const value = Math.floor(Math.random() * (max - min + 1)) + min;
      data.push({
        date: date.toISOString(),
        value,
      });
    }
    return data;
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadProgressData();
    setRefreshing(false);
  };

  const periodOptions: { value: TimePeriod; label: string }[] = [
    { value: 'week', label: 'This Week' },
    { value: 'month', label: 'This Month' },
    { value: 'year', label: 'This Year' },
    { value: 'all', label: 'All Time' },
  ];

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
          <Text style={styles.title}>Learning Progress</Text>
          <Text style={styles.subtitle}>Track mastery and growth</Text>
        </View>

        {/* Time Period Selector */}
        <View style={styles.periodSelector}>
          {periodOptions.map((option) => (
            <TouchableOpacity
              key={option.value}
              style={[
                styles.periodButton,
                selectedPeriod === option.value && styles.periodButtonActive,
              ]}
              onPress={() => setSelectedPeriod(option.value)}
              activeOpacity={0.7}
            >
              <Text
                style={[
                  styles.periodText,
                  selectedPeriod === option.value && styles.periodTextActive,
                ]}
              >
                {option.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {progressData && (
          <>
            {/* Overall Stats */}
            <Card style={styles.statsCard}>
              <Text style={styles.sectionTitle}>Overview</Text>
              <View style={styles.overallStats}>
                <OverallStat
                  label="Total Hours"
                  value={progressData.overallStats.totalHours.toFixed(1)}
                  icon="⏱️"
                  color="#2196F3"
                />
                <OverallStat
                  label="Avg Confidence"
                  value={`${progressData.overallStats.averageConfidence}%`}
                  icon="🎯"
                  color="#4CAF50"
                />
                <OverallStat
                  label="Questions"
                  value={progressData.overallStats.questionsAnswered.toString()}
                  icon="❓"
                  color="#FF9800"
                />
                <OverallStat
                  label="Topics"
                  value={progressData.overallStats.topicsExplored.toString()}
                  icon="📚"
                  color="#9C27B0"
                />
              </View>
            </Card>

            {/* Subject Breakdown */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Subject Breakdown</Text>
              <Text style={styles.sectionSubtitle}>
                Progress by subject area
              </Text>
              {progressData.subjectProgress.map((subject, index) => (
                <SubjectCard
                  key={index}
                  subject={subject}
                  onPress={() => console.log('Subject pressed:', subject.subject)}
                />
              ))}
            </View>

            {/* Confidence Trend */}
            <Card style={styles.chartCard}>
              <ProgressChart
                data={progressData.confidenceTrend}
                title="Confidence Level Trend"
                color="#4CAF50"
                height={200}
              />
            </Card>

            {/* Engagement Trend */}
            <Card style={styles.chartCard}>
              <ProgressChart
                data={progressData.engagementTrend}
                title="Engagement Level Trend"
                color="#2196F3"
                height={200}
              />
            </Card>

            {/* Strengths & Areas for Improvement */}
            <View style={styles.insightsRow}>
              <Card style={styles.insightCard}>
                <Text style={styles.insightTitle}>Top Strengths</Text>
                <View style={styles.insightList}>
                  {progressData.topStrengths.map((strength, index) => (
                    <View key={index} style={styles.insightItem}>
                      <Text style={styles.insightBullet}>✓</Text>
                      <Text style={styles.insightText}>{strength}</Text>
                    </View>
                  ))}
                </View>
              </Card>

              <Card style={styles.insightCard}>
                <Text style={styles.insightTitle}>Areas to Improve</Text>
                <View style={styles.insightList}>
                  {progressData.areasForImprovement.map((area, index) => (
                    <View key={index} style={styles.insightItem}>
                      <Text style={styles.insightBullet}>→</Text>
                      <Text style={styles.insightText}>{area}</Text>
                    </View>
                  ))}
                </View>
              </Card>
            </View>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
};

const OverallStat: React.FC<{
  label: string;
  value: string;
  icon: string;
  color: string;
}> = ({ label, value, icon, color }) => (
  <View style={styles.overallStat}>
    <View style={[styles.statIconContainer, { backgroundColor: `${color}20` }]}>
      <Text style={styles.statIcon}>{icon}</Text>
    </View>
    <Text style={[styles.statValue, { color }]}>{value}</Text>
    <Text style={styles.statLabel}>{label}</Text>
  </View>
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
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#333333',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 15,
    color: '#666666',
  },
  periodSelector: {
    flexDirection: 'row',
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 4,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 2,
  },
  periodButton: {
    flex: 1,
    paddingVertical: 8,
    paddingHorizontal: 4,
    borderRadius: 8,
    alignItems: 'center',
  },
  periodButtonActive: {
    backgroundColor: '#4A90A4',
  },
  periodText: {
    fontSize: 12,
    fontWeight: '500',
    color: '#666666',
  },
  periodTextActive: {
    color: '#FFFFFF',
    fontWeight: '600',
  },
  statsCard: {
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333333',
    marginBottom: 4,
  },
  sectionSubtitle: {
    fontSize: 13,
    color: '#999999',
    marginBottom: 12,
  },
  overallStats: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 12,
    gap: 8,
  },
  overallStat: {
    flex: 1,
    alignItems: 'center',
  },
  statIconContainer: {
    width: 48,
    height: 48,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  statIcon: {
    fontSize: 24,
  },
  statValue: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 11,
    color: '#666666',
    textAlign: 'center',
  },
  section: {
    marginBottom: 16,
  },
  chartCard: {
    marginBottom: 16,
  },
  insightsRow: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 16,
  },
  insightCard: {
    flex: 1,
  },
  insightTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: '#333333',
    marginBottom: 12,
  },
  insightList: {
    gap: 8,
  },
  insightItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  insightBullet: {
    fontSize: 14,
    color: '#4A90A4',
    marginRight: 8,
    marginTop: 1,
  },
  insightText: {
    flex: 1,
    fontSize: 13,
    color: '#666666',
    lineHeight: 18,
  },
});
