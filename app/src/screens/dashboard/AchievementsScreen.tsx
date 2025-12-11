/**
 * AchievementsScreen
 * Display earned achievements, milestones, and streak tracking
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  TouchableOpacity,
  Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { AchievementBadge } from '../../components/dashboard/AchievementBadge';
import { Card } from '../../components/common/Card';
import { Achievement } from '../../types';

type AchievementCategory = 'all' | 'reading' | 'math' | 'science' | 'streak' | 'milestone';

interface AchievementProgress {
  achievement: Achievement;
  progress: number; // 0-100
  locked: boolean;
}

interface StreakData {
  currentStreak: number;
  longestStreak: number;
  lastActivityDate: string;
}

export const AchievementsScreen: React.FC = () => {
  const [refreshing, setRefreshing] = useState(false);
  const [earnedAchievements, setEarnedAchievements] = useState<Achievement[]>([]);
  const [lockedAchievements, setLockedAchievements] = useState<AchievementProgress[]>([]);
  const [streakData, setStreakData] = useState<StreakData | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<AchievementCategory>('all');
  const [selectedAchievement, setSelectedAchievement] = useState<Achievement | null>(null);
  const [detailsModalVisible, setDetailsModalVisible] = useState(false);

  useEffect(() => {
    loadAchievements();
  }, []);

  const loadAchievements = async () => {
    // TODO: Replace with actual API call
    // Mock data for demonstration
    const earned: Achievement[] = [
      {
        id: '1',
        childId: 'child1',
        title: 'First Steps',
        description: 'Complete your first learning session',
        category: 'milestone',
        icon: '🎯',
        earnedAt: new Date(Date.now() - 7 * 86400000).toISOString(),
        rarity: 'common',
      },
      {
        id: '2',
        childId: 'child1',
        title: 'Math Whiz',
        description: 'Solve 100 math problems',
        category: 'math',
        icon: '🔢',
        earnedAt: new Date(Date.now() - 5 * 86400000).toISOString(),
        rarity: 'rare',
      },
      {
        id: '3',
        childId: 'child1',
        title: 'Book Worm',
        description: 'Read for 10 hours total',
        category: 'reading',
        icon: '📚',
        earnedAt: new Date(Date.now() - 3 * 86400000).toISOString(),
        rarity: 'rare',
      },
      {
        id: '4',
        childId: 'child1',
        title: 'Week Warrior',
        description: 'Maintain a 7-day learning streak',
        category: 'streak',
        icon: '🔥',
        earnedAt: new Date(Date.now() - 1 * 86400000).toISOString(),
        rarity: 'epic',
      },
      {
        id: '5',
        childId: 'child1',
        title: 'Science Explorer',
        description: 'Complete 50 science topics',
        category: 'science',
        icon: '🔬',
        earnedAt: new Date(Date.now() - 2 * 86400000).toISOString(),
        rarity: 'rare',
      },
      {
        id: '6',
        childId: 'child1',
        title: 'Master Student',
        description: 'Achieve 90% mastery in any subject',
        category: 'milestone',
        icon: '🎓',
        earnedAt: new Date().toISOString(),
        rarity: 'legendary',
      },
    ];

    const locked: AchievementProgress[] = [
      {
        achievement: {
          id: '7',
          childId: 'child1',
          title: 'Century Club',
          description: 'Complete 100 learning sessions',
          category: 'milestone',
          icon: '💯',
          earnedAt: '',
          rarity: 'epic',
        },
        progress: 65,
        locked: true,
      },
      {
        achievement: {
          id: '8',
          childId: 'child1',
          title: 'Marathon Learner',
          description: 'Learn for 50 hours total',
          category: 'milestone',
          icon: '⏰',
          earnedAt: '',
          rarity: 'legendary',
        },
        progress: 42,
        locked: true,
      },
      {
        achievement: {
          id: '9',
          childId: 'child1',
          title: 'Question Master',
          description: 'Ask 500 questions',
          category: 'milestone',
          icon: '❓',
          earnedAt: '',
          rarity: 'epic',
        },
        progress: 78,
        locked: true,
      },
    ];

    setEarnedAchievements(earned);
    setLockedAchievements(locked);
    setStreakData({
      currentStreak: 7,
      longestStreak: 12,
      lastActivityDate: new Date().toISOString(),
    });
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadAchievements();
    setRefreshing(false);
  };

  const filterAchievements = (achievements: Achievement[]): Achievement[] => {
    if (selectedCategory === 'all') {
      return achievements;
    }
    return achievements.filter((a) => a.category === selectedCategory);
  };

  const handleAchievementPress = (achievement: Achievement) => {
    setSelectedAchievement(achievement);
    setDetailsModalVisible(true);
  };

  const categories: { value: AchievementCategory; label: string; icon: string }[] = [
    { value: 'all', label: 'All', icon: '🏆' },
    { value: 'milestone', label: 'Milestones', icon: '🎯' },
    { value: 'streak', label: 'Streaks', icon: '🔥' },
    { value: 'reading', label: 'Reading', icon: '📚' },
    { value: 'math', label: 'Math', icon: '🔢' },
    { value: 'science', label: 'Science', icon: '🔬' },
  ];

  const filteredEarned = filterAchievements(earnedAchievements);
  const totalPoints = earnedAchievements.length * 100;

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
          <Text style={styles.title}>Achievements</Text>
          <Text style={styles.subtitle}>Celebrate your learning journey</Text>
        </View>

        {/* Stats Overview */}
        <Card style={styles.statsCard}>
          <View style={styles.statsRow}>
            <View style={styles.statItem}>
              <Text style={styles.statValue}>{earnedAchievements.length}</Text>
              <Text style={styles.statLabel}>Earned</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statItem}>
              <Text style={styles.statValue}>{totalPoints}</Text>
              <Text style={styles.statLabel}>Points</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statItem}>
              <Text style={styles.statValue}>
                {Math.round((earnedAchievements.length / (earnedAchievements.length + lockedAchievements.length)) * 100)}%
              </Text>
              <Text style={styles.statLabel}>Complete</Text>
            </View>
          </View>
        </Card>

        {/* Streak Card */}
        {streakData && (
          <Card style={styles.streakCard}>
            <View style={styles.streakHeader}>
              <Text style={styles.streakTitle}>Learning Streak</Text>
              <Text style={styles.streakIcon}>🔥</Text>
            </View>
            <View style={styles.streakContent}>
              <View style={styles.streakItem}>
                <Text style={styles.streakValue}>{streakData.currentStreak}</Text>
                <Text style={styles.streakLabel}>Current Streak</Text>
              </View>
              <View style={styles.streakDivider} />
              <View style={styles.streakItem}>
                <Text style={styles.streakValue}>{streakData.longestStreak}</Text>
                <Text style={styles.streakLabel}>Longest Streak</Text>
              </View>
            </View>
            <Text style={styles.streakMotivation}>
              Keep it up! Learn today to maintain your streak.
            </Text>
          </Card>
        )}

        {/* Category Filter */}
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.categoryScroll}
          contentContainerStyle={styles.categoryScrollContent}
        >
          {categories.map((category) => (
            <TouchableOpacity
              key={category.value}
              style={[
                styles.categoryChip,
                selectedCategory === category.value && styles.categoryChipActive,
              ]}
              onPress={() => setSelectedCategory(category.value)}
              activeOpacity={0.7}
            >
              <Text style={styles.categoryIcon}>{category.icon}</Text>
              <Text
                style={[
                  styles.categoryLabel,
                  selectedCategory === category.value && styles.categoryLabelActive,
                ]}
              >
                {category.label}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* Earned Achievements */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>
            Earned Achievements ({filteredEarned.length})
          </Text>
          <View style={styles.achievementGrid}>
            {filteredEarned.map((achievement) => (
              <AchievementBadge
                key={achievement.id}
                achievement={achievement}
                onPress={() => handleAchievementPress(achievement)}
                size="medium"
                style={styles.achievementBadge}
              />
            ))}
          </View>
          {filteredEarned.length === 0 && (
            <View style={styles.emptyState}>
              <Text style={styles.emptyText}>No achievements in this category yet</Text>
            </View>
          )}
        </View>

        {/* In Progress / Locked Achievements */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>In Progress</Text>
          <View style={styles.achievementGrid}>
            {lockedAchievements.map((item) => (
              <AchievementBadge
                key={item.achievement.id}
                achievement={item.achievement}
                locked={true}
                progress={item.progress}
                size="medium"
                style={styles.achievementBadge}
              />
            ))}
          </View>
        </View>
      </ScrollView>

      {/* Achievement Details Modal */}
      <Modal
        visible={detailsModalVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setDetailsModalVisible(false)}
      >
        <TouchableOpacity
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setDetailsModalVisible(false)}
        >
          <View style={styles.modalContent}>
            {selectedAchievement && (
              <>
                <View style={styles.modalBadge}>
                  <AchievementBadge
                    achievement={selectedAchievement}
                    size="large"
                  />
                </View>
                <Text style={styles.modalTitle}>{selectedAchievement.title}</Text>
                <Text style={styles.modalDescription}>
                  {selectedAchievement.description}
                </Text>
                <View style={styles.modalDetails}>
                  <DetailRow label="Category" value={selectedAchievement.category} />
                  <DetailRow label="Rarity" value={selectedAchievement.rarity} />
                  <DetailRow
                    label="Earned"
                    value={new Date(selectedAchievement.earnedAt).toLocaleDateString('en-US', {
                      month: 'long',
                      day: 'numeric',
                      year: 'numeric',
                    })}
                  />
                </View>
                <TouchableOpacity
                  style={styles.modalCloseButton}
                  onPress={() => setDetailsModalVisible(false)}
                  activeOpacity={0.7}
                >
                  <Text style={styles.modalCloseText}>Close</Text>
                </TouchableOpacity>
              </>
            )}
          </View>
        </TouchableOpacity>
      </Modal>
    </SafeAreaView>
  );
};

const DetailRow: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <View style={styles.detailRow}>
    <Text style={styles.detailLabel}>{label}</Text>
    <Text style={styles.detailValue}>{value}</Text>
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
  statsCard: {
    marginBottom: 16,
  },
  statsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
  },
  statItem: {
    flex: 1,
    alignItems: 'center',
  },
  statValue: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#4A90A4',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 12,
    color: '#666666',
  },
  statDivider: {
    width: 1,
    height: 40,
    backgroundColor: '#E0E0E0',
  },
  streakCard: {
    marginBottom: 16,
    backgroundColor: '#FFF8E1',
  },
  streakHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  streakTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333333',
  },
  streakIcon: {
    fontSize: 32,
  },
  streakContent: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  streakItem: {
    flex: 1,
    alignItems: 'center',
  },
  streakValue: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#FF6B35',
    marginBottom: 4,
  },
  streakLabel: {
    fontSize: 12,
    color: '#666666',
  },
  streakDivider: {
    width: 1,
    height: 50,
    backgroundColor: '#FFD54F',
    marginHorizontal: 20,
  },
  streakMotivation: {
    fontSize: 13,
    color: '#FF6B35',
    textAlign: 'center',
    fontWeight: '500',
  },
  categoryScroll: {
    marginBottom: 16,
  },
  categoryScrollContent: {
    paddingRight: 16,
    gap: 8,
  },
  categoryChip: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#E0E0E0',
    gap: 6,
  },
  categoryChipActive: {
    backgroundColor: '#4A90A4',
    borderColor: '#4A90A4',
  },
  categoryIcon: {
    fontSize: 16,
  },
  categoryLabel: {
    fontSize: 13,
    fontWeight: '500',
    color: '#666666',
  },
  categoryLabelActive: {
    color: '#FFFFFF',
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333333',
    marginBottom: 16,
  },
  achievementGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  achievementBadge: {
    width: '31%',
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 40,
  },
  emptyText: {
    fontSize: 14,
    color: '#999999',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 24,
    width: '85%',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 12,
    elevation: 10,
  },
  modalBadge: {
    marginBottom: 20,
  },
  modalTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#333333',
    marginBottom: 8,
    textAlign: 'center',
  },
  modalDescription: {
    fontSize: 15,
    color: '#666666',
    textAlign: 'center',
    marginBottom: 24,
    lineHeight: 22,
  },
  modalDetails: {
    width: '100%',
    marginBottom: 24,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  detailLabel: {
    fontSize: 14,
    color: '#999999',
  },
  detailValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333333',
    textTransform: 'capitalize',
  },
  modalCloseButton: {
    backgroundColor: '#4A90A4',
    paddingHorizontal: 32,
    paddingVertical: 12,
    borderRadius: 12,
  },
  modalCloseText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
  },
});
