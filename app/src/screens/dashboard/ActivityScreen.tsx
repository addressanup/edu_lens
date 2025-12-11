/**
 * ActivityScreen
 * Activity log with session history, filtering, and export functionality
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
  FlatList,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ActivityItem } from '../../components/dashboard/ActivityItem';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { LearningActivity, LearningSession } from '../../types';

type FilterType = 'all' | 'reading' | 'tutoring' | 'translation' | 'ocr' | 'exploration';
type DateFilter = 'today' | 'week' | 'month' | 'all';

interface SessionDetails {
  session: LearningSession;
  activities: LearningActivity[];
}

export const ActivityScreen: React.FC = () => {
  const [refreshing, setRefreshing] = useState(false);
  const [activities, setActivities] = useState<LearningActivity[]>([]);
  const [filteredActivities, setFilteredActivities] = useState<LearningActivity[]>([]);
  const [selectedFilter, setSelectedFilter] = useState<FilterType>('all');
  const [selectedDateFilter, setSelectedDateFilter] = useState<DateFilter>('week');
  const [filterModalVisible, setFilterModalVisible] = useState(false);
  const [selectedActivity, setSelectedActivity] = useState<LearningActivity | null>(null);

  useEffect(() => {
    loadActivities();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [activities, selectedFilter, selectedDateFilter]);

  const loadActivities = async () => {
    // TODO: Replace with actual API call
    // Mock data for demonstration
    const mockActivities: LearningActivity[] = [];
    const types: FilterType[] = ['reading', 'tutoring', 'translation', 'ocr', 'exploration'];
    const subjects = ['Math', 'Reading', 'Science', 'Social Studies'];

    for (let i = 0; i < 20; i++) {
      const daysAgo = Math.floor(Math.random() * 30);
      const date = new Date(Date.now() - daysAgo * 86400000);

      mockActivities.push({
        id: `activity-${i}`,
        sessionId: `session-${Math.floor(i / 3)}`,
        type: types[Math.floor(Math.random() * types.length)] as any,
        subject: subjects[Math.floor(Math.random() * subjects.length)],
        topic: `Topic ${i + 1}`,
        startTime: date.toISOString(),
        duration: Math.floor(Math.random() * 1800) + 300,
        questionsAsked: Math.floor(Math.random() * 15) + 1,
        answersProvided: Math.floor(Math.random() * 15) + 1,
        confidence: Math.floor(Math.random() * 30) + 70,
        engagement: Math.floor(Math.random() * 30) + 70,
        metadata: {},
      });
    }

    setActivities(mockActivities.sort((a, b) =>
      new Date(b.startTime).getTime() - new Date(a.startTime).getTime()
    ));
  };

  const applyFilters = () => {
    let filtered = activities;

    // Apply type filter
    if (selectedFilter !== 'all') {
      filtered = filtered.filter((activity) => activity.type === selectedFilter);
    }

    // Apply date filter
    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const startOfWeek = new Date(now.getTime() - 7 * 86400000);
    const startOfMonth = new Date(now.getTime() - 30 * 86400000);

    filtered = filtered.filter((activity) => {
      const activityDate = new Date(activity.startTime);
      switch (selectedDateFilter) {
        case 'today':
          return activityDate >= startOfToday;
        case 'week':
          return activityDate >= startOfWeek;
        case 'month':
          return activityDate >= startOfMonth;
        default:
          return true;
      }
    });

    setFilteredActivities(filtered);
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadActivities();
    setRefreshing(false);
  };

  const handleExport = () => {
    // TODO: Implement actual export functionality
    Alert.alert(
      'Export Activities',
      'Export activity log as CSV or PDF?',
      [
        {
          text: 'CSV',
          onPress: () => Alert.alert('Success', 'Activity log exported as CSV'),
        },
        {
          text: 'PDF',
          onPress: () => Alert.alert('Success', 'Activity log exported as PDF'),
        },
        { text: 'Cancel', style: 'cancel' },
      ]
    );
  };

  const getTotalDuration = (): string => {
    const totalSeconds = filteredActivities.reduce(
      (sum, activity) => sum + activity.duration,
      0
    );
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
  };

  const filterOptions: { value: FilterType; label: string; icon: string }[] = [
    { value: 'all', label: 'All Activities', icon: '📋' },
    { value: 'reading', label: 'Reading', icon: '📖' },
    { value: 'tutoring', label: 'Tutoring', icon: '👨‍🏫' },
    { value: 'translation', label: 'Translation', icon: '🌐' },
    { value: 'ocr', label: 'OCR', icon: '📷' },
    { value: 'exploration', label: 'Exploration', icon: '🔍' },
  ];

  const dateFilterOptions: { value: DateFilter; label: string }[] = [
    { value: 'today', label: 'Today' },
    { value: 'week', label: 'This Week' },
    { value: 'month', label: 'This Month' },
    { value: 'all', label: 'All Time' },
  ];

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>Activity Log</Text>
          <Text style={styles.subtitle}>Session history and details</Text>
        </View>
      </View>

      {/* Summary Card */}
      <Card style={styles.summaryCard}>
        <View style={styles.summaryRow}>
          <View style={styles.summaryItem}>
            <Text style={styles.summaryValue}>{filteredActivities.length}</Text>
            <Text style={styles.summaryLabel}>Activities</Text>
          </View>
          <View style={styles.summaryItem}>
            <Text style={styles.summaryValue}>{getTotalDuration()}</Text>
            <Text style={styles.summaryLabel}>Total Time</Text>
          </View>
          <View style={styles.summaryItem}>
            <Text style={styles.summaryValue}>
              {filteredActivities.reduce((sum, a) => sum + a.questionsAsked, 0)}
            </Text>
            <Text style={styles.summaryLabel}>Questions</Text>
          </View>
        </View>
      </Card>

      {/* Filter Bar */}
      <View style={styles.filterBar}>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.filterScrollContent}
        >
          {dateFilterOptions.map((option) => (
            <TouchableOpacity
              key={option.value}
              style={[
                styles.filterChip,
                selectedDateFilter === option.value && styles.filterChipActive,
              ]}
              onPress={() => setSelectedDateFilter(option.value)}
              activeOpacity={0.7}
            >
              <Text
                style={[
                  styles.filterChipText,
                  selectedDateFilter === option.value && styles.filterChipTextActive,
                ]}
              >
                {option.label}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        <TouchableOpacity
          style={styles.moreFiltersButton}
          onPress={() => setFilterModalVisible(true)}
          activeOpacity={0.7}
        >
          <Text style={styles.moreFiltersText}>Type ▼</Text>
        </TouchableOpacity>
      </View>

      {/* Activity List */}
      <FlatList
        data={filteredActivities}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <ActivityItem
            activity={item}
            onPress={() => setSelectedActivity(item)}
            style={styles.activityItem}
          />
        )}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Text style={styles.emptyIcon}>📭</Text>
            <Text style={styles.emptyText}>No activities found</Text>
            <Text style={styles.emptySubtext}>
              Try adjusting your filters
            </Text>
          </View>
        }
      />

      {/* Export Button */}
      {filteredActivities.length > 0 && (
        <View style={styles.exportContainer}>
          <Button
            title="Export Activity Log"
            onPress={handleExport}
            variant="outline"
            icon={<Text style={styles.exportIcon}>📤</Text>}
          />
        </View>
      )}

      {/* Filter Modal */}
      <Modal
        visible={filterModalVisible}
        transparent
        animationType="slide"
        onRequestClose={() => setFilterModalVisible(false)}
      >
        <TouchableOpacity
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setFilterModalVisible(false)}
        >
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Filter by Type</Text>
              <TouchableOpacity onPress={() => setFilterModalVisible(false)}>
                <Text style={styles.closeButton}>✕</Text>
              </TouchableOpacity>
            </View>
            <ScrollView>
              {filterOptions.map((option) => (
                <TouchableOpacity
                  key={option.value}
                  style={[
                    styles.filterOption,
                    selectedFilter === option.value && styles.filterOptionActive,
                  ]}
                  onPress={() => {
                    setSelectedFilter(option.value);
                    setFilterModalVisible(false);
                  }}
                  activeOpacity={0.7}
                >
                  <Text style={styles.filterIcon}>{option.icon}</Text>
                  <Text style={styles.filterLabel}>{option.label}</Text>
                  {selectedFilter === option.value && (
                    <Text style={styles.checkmark}>✓</Text>
                  )}
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>
        </TouchableOpacity>
      </Modal>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F7FA',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: 16,
    paddingBottom: 8,
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
  summaryCard: {
    marginHorizontal: 16,
    marginBottom: 12,
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  summaryItem: {
    alignItems: 'center',
  },
  summaryValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#4A90A4',
    marginBottom: 4,
  },
  summaryLabel: {
    fontSize: 12,
    color: '#666666',
  },
  filterBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingLeft: 16,
    marginBottom: 12,
  },
  filterScrollContent: {
    paddingRight: 8,
    gap: 8,
  },
  filterChip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#E0E0E0',
  },
  filterChipActive: {
    backgroundColor: '#4A90A4',
    borderColor: '#4A90A4',
  },
  filterChipText: {
    fontSize: 13,
    fontWeight: '500',
    color: '#666666',
  },
  filterChipTextActive: {
    color: '#FFFFFF',
  },
  moreFiltersButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    marginRight: 16,
  },
  moreFiltersText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#4A90A4',
  },
  listContent: {
    padding: 16,
    paddingTop: 0,
  },
  activityItem: {
    marginBottom: 8,
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 16,
  },
  emptyText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#666666',
    marginBottom: 8,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#999999',
  },
  exportContainer: {
    padding: 16,
    paddingTop: 8,
    backgroundColor: '#FFFFFF',
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
  },
  exportIcon: {
    fontSize: 16,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '70%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333333',
  },
  closeButton: {
    fontSize: 24,
    color: '#999999',
    paddingHorizontal: 8,
  },
  filterOption: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#F5F5F5',
  },
  filterOptionActive: {
    backgroundColor: '#E8F4F8',
  },
  filterIcon: {
    fontSize: 24,
    marginRight: 12,
  },
  filterLabel: {
    flex: 1,
    fontSize: 16,
    color: '#333333',
  },
  checkmark: {
    fontSize: 18,
    color: '#4A90A4',
    fontWeight: '600',
  },
});
