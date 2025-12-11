/**
 * ContentFiltersScreen
 * Screen for managing content filtering and subject restrictions
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
import { SubjectToggle, Subject } from '../../components/controls/SubjectToggle';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { useChild } from '../../hooks/useChild';

interface ContentFilters {
  ageAppropriate: boolean;
  enabledSubjects: string[];
  restrictedTopics: string[];
  difficultyLevel: 'beginner' | 'intermediate' | 'advanced' | 'adaptive';
  explicitContentFilter: boolean;
  safeSearchEnabled: boolean;
}

const AVAILABLE_SUBJECTS: Subject[] = [
  {
    id: 'math',
    name: 'Mathematics',
    icon: '🔢',
    description: 'Arithmetic, algebra, geometry, calculus',
    enabled: true,
  },
  {
    id: 'science',
    name: 'Science',
    icon: '🔬',
    description: 'Physics, chemistry, biology, earth science',
    enabled: true,
  },
  {
    id: 'reading',
    name: 'Reading & Literature',
    icon: '📚',
    description: 'Reading comprehension, literature analysis',
    enabled: true,
  },
  {
    id: 'language',
    name: 'Languages',
    icon: '🌍',
    description: 'Foreign languages, translation',
    enabled: true,
  },
  {
    id: 'history',
    name: 'History',
    icon: '🏛️',
    description: 'World history, social studies',
    enabled: true,
  },
  {
    id: 'geography',
    name: 'Geography',
    icon: '🗺️',
    description: 'World geography, maps, cultures',
    enabled: true,
  },
  {
    id: 'arts',
    name: 'Arts & Music',
    icon: '🎨',
    description: 'Visual arts, music theory, appreciation',
    enabled: false,
  },
  {
    id: 'coding',
    name: 'Coding & Technology',
    icon: '💻',
    description: 'Programming, computer science basics',
    enabled: false,
  },
];

const RESTRICTED_TOPICS = [
  'Violence',
  'Adult Content',
  'Gambling',
  'Weapons',
  'Drugs & Alcohol',
  'Political Extremism',
  'Self-Harm',
  'Hate Speech',
];

export const ContentFiltersScreen: React.FC = () => {
  const navigation = useNavigation();
  const { activeChild, updatePreferences, isLoading } = useChild();

  const [filters, setFilters] = useState<ContentFilters>({
    ageAppropriate: true,
    enabledSubjects: ['math', 'science', 'reading', 'language', 'history', 'geography'],
    restrictedTopics: RESTRICTED_TOPICS,
    difficultyLevel: 'adaptive',
    explicitContentFilter: true,
    safeSearchEnabled: true,
  });

  const [subjects, setSubjects] = useState<Subject[]>(AVAILABLE_SUBJECTS);
  const [hasChanges, setHasChanges] = useState(false);

  // Load current child's preferences
  useEffect(() => {
    if (activeChild?.preferences) {
      const enabledSubjects = activeChild.preferences.subjects || [];
      setFilters((prev) => ({
        ...prev,
        enabledSubjects,
        difficultyLevel: activeChild.preferences.difficultyLevel || 'adaptive',
      }));

      // Update subjects enabled state
      setSubjects(
        AVAILABLE_SUBJECTS.map((subject) => ({
          ...subject,
          enabled: enabledSubjects.includes(subject.id),
        }))
      );
    }
  }, [activeChild]);

  const handleSubjectToggle = (subjectId: string, enabled: boolean) => {
    setSubjects((prev) =>
      prev.map((subject) =>
        subject.id === subjectId ? { ...subject, enabled } : subject
      )
    );

    setFilters((prev) => ({
      ...prev,
      enabledSubjects: enabled
        ? [...prev.enabledSubjects, subjectId]
        : prev.enabledSubjects.filter((id) => id !== subjectId),
    }));

    setHasChanges(true);
  };

  const handleDifficultyChange = (level: ContentFilters['difficultyLevel']) => {
    setFilters((prev) => ({ ...prev, difficultyLevel: level }));
    setHasChanges(true);
  };

  const handleFilterToggle = (key: keyof ContentFilters) => {
    setFilters((prev) => ({
      ...prev,
      [key]: !prev[key as keyof typeof prev],
    }));
    setHasChanges(true);
  };

  const handleSave = async () => {
    if (!activeChild) {
      Alert.alert('Error', 'No active child selected');
      return;
    }

    const success = await updatePreferences(activeChild.id, {
      subjects: filters.enabledSubjects,
      difficultyLevel: filters.difficultyLevel,
    });

    if (success) {
      Alert.alert('Success', 'Content filters updated successfully');
      setHasChanges(false);
    } else {
      Alert.alert('Error', 'Failed to update content filters');
    }
  };

  const handleEnableAll = () => {
    setSubjects((prev) => prev.map((subject) => ({ ...subject, enabled: true })));
    setFilters((prev) => ({
      ...prev,
      enabledSubjects: AVAILABLE_SUBJECTS.map((s) => s.id),
    }));
    setHasChanges(true);
  };

  const handleDisableAll = () => {
    setSubjects((prev) => prev.map((subject) => ({ ...subject, enabled: false })));
    setFilters((prev) => ({ ...prev, enabledSubjects: [] }));
    setHasChanges(true);
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
          <Text style={styles.title}>Content Filters</Text>
          <Text style={styles.subtitle}>
            Manage content for {activeChild.name}
          </Text>
        </View>

        {/* Age-Appropriate Content */}
        <Card style={styles.card}>
          <Text style={styles.cardTitle}>Age-Appropriate Content</Text>
          <Text style={styles.cardDescription}>
            Automatically filter content based on child's age
          </Text>

          <View style={styles.ageInfo}>
            <View style={styles.ageInfoRow}>
              <Text style={styles.ageLabel}>Child's Age:</Text>
              <Text style={styles.ageValue}>{activeChild.age} years</Text>
            </View>
            <View style={styles.ageInfoRow}>
              <Text style={styles.ageLabel}>Grade Level:</Text>
              <Text style={styles.ageValue}>{activeChild.grade}</Text>
            </View>
          </View>

          <TouchableOpacity
            style={styles.filterToggle}
            onPress={() => handleFilterToggle('ageAppropriate')}
          >
            <View>
              <Text style={styles.filterTitle}>Age-Appropriate Filter</Text>
              <Text style={styles.filterDescription}>
                Only show content suitable for {activeChild.age} year olds
              </Text>
            </View>
            <View
              style={[
                styles.toggle,
                filters.ageAppropriate && styles.toggleActive,
              ]}
            >
              <View
                style={[
                  styles.toggleThumb,
                  filters.ageAppropriate && styles.toggleThumbActive,
                ]}
              />
            </View>
          </TouchableOpacity>
        </Card>

        {/* Subject Controls */}
        <Card style={styles.card}>
          <View style={styles.cardHeader}>
            <View>
              <Text style={styles.cardTitle}>Enabled Subjects</Text>
              <Text style={styles.cardDescription}>
                Choose which subjects are available
              </Text>
            </View>
            <View style={styles.headerActions}>
              <TouchableOpacity onPress={handleEnableAll}>
                <Text style={styles.actionLink}>Enable All</Text>
              </TouchableOpacity>
              <Text style={styles.actionSeparator}>|</Text>
              <TouchableOpacity onPress={handleDisableAll}>
                <Text style={styles.actionLink}>Disable All</Text>
              </TouchableOpacity>
            </View>
          </View>

          <View style={styles.subjectList}>
            {subjects.map((subject) => (
              <SubjectToggle
                key={subject.id}
                subject={subject}
                onToggle={handleSubjectToggle}
              />
            ))}
          </View>
        </Card>

        {/* Difficulty Level */}
        <Card style={styles.card}>
          <Text style={styles.cardTitle}>Difficulty Level</Text>
          <Text style={styles.cardDescription}>
            Set the maximum difficulty level for content
          </Text>

          <View style={styles.difficultyOptions}>
            {(['beginner', 'intermediate', 'advanced', 'adaptive'] as const).map(
              (level) => (
                <TouchableOpacity
                  key={level}
                  style={[
                    styles.difficultyOption,
                    filters.difficultyLevel === level && styles.difficultyOptionActive,
                  ]}
                  onPress={() => handleDifficultyChange(level)}
                >
                  <Text
                    style={[
                      styles.difficultyText,
                      filters.difficultyLevel === level && styles.difficultyTextActive,
                    ]}
                  >
                    {level.charAt(0).toUpperCase() + level.slice(1)}
                  </Text>
                </TouchableOpacity>
              )
            )}
          </View>

          <View style={styles.infoBox}>
            <Text style={styles.infoText}>
              💡 Adaptive mode automatically adjusts difficulty based on your child's
              performance
            </Text>
          </View>
        </Card>

        {/* Safety Filters */}
        <Card style={styles.card}>
          <Text style={styles.cardTitle}>Safety Filters</Text>
          <Text style={styles.cardDescription}>
            Additional content protection
          </Text>

          <TouchableOpacity
            style={styles.filterToggle}
            onPress={() => handleFilterToggle('explicitContentFilter')}
          >
            <View>
              <Text style={styles.filterTitle}>Block Explicit Content</Text>
              <Text style={styles.filterDescription}>
                Filter out inappropriate language and images
              </Text>
            </View>
            <View
              style={[
                styles.toggle,
                filters.explicitContentFilter && styles.toggleActive,
              ]}
            >
              <View
                style={[
                  styles.toggleThumb,
                  filters.explicitContentFilter && styles.toggleThumbActive,
                ]}
              />
            </View>
          </TouchableOpacity>

          <View style={styles.divider} />

          <TouchableOpacity
            style={styles.filterToggle}
            onPress={() => handleFilterToggle('safeSearchEnabled')}
          >
            <View>
              <Text style={styles.filterTitle}>Safe Search</Text>
              <Text style={styles.filterDescription}>
                Enable safe search for all queries
              </Text>
            </View>
            <View
              style={[
                styles.toggle,
                filters.safeSearchEnabled && styles.toggleActive,
              ]}
            >
              <View
                style={[
                  styles.toggleThumb,
                  filters.safeSearchEnabled && styles.toggleThumbActive,
                ]}
              />
            </View>
          </TouchableOpacity>
        </Card>

        {/* Restricted Topics */}
        <Card style={styles.card}>
          <Text style={styles.cardTitle}>Restricted Topics</Text>
          <Text style={styles.cardDescription}>
            Always blocked from content
          </Text>

          <View style={styles.topicGrid}>
            {filters.restrictedTopics.map((topic) => (
              <View key={topic} style={styles.topicBadge}>
                <Text style={styles.topicText}>{topic}</Text>
              </View>
            ))}
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
  cardHeader: {
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
  },
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
  },
  actionLink: {
    fontSize: 14,
    color: '#4A90A4',
    fontWeight: '600',
  },
  actionSeparator: {
    fontSize: 14,
    color: '#CCCCCC',
    marginHorizontal: 8,
  },
  ageInfo: {
    backgroundColor: '#F8FAFB',
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
  },
  ageInfoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  ageLabel: {
    fontSize: 14,
    color: '#666666',
  },
  ageValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333333',
  },
  filterToggle: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
  },
  filterTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333333',
    marginBottom: 4,
  },
  filterDescription: {
    fontSize: 14,
    color: '#999999',
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
  subjectList: {
    marginTop: 12,
  },
  difficultyOptions: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 16,
    marginBottom: 16,
  },
  difficultyOption: {
    flex: 1,
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 12,
    backgroundColor: '#F8FAFB',
    borderWidth: 2,
    borderColor: '#E0E0E0',
    alignItems: 'center',
  },
  difficultyOptionActive: {
    backgroundColor: '#E8F4F8',
    borderColor: '#4A90A4',
  },
  difficultyText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#666666',
  },
  difficultyTextActive: {
    color: '#4A90A4',
  },
  topicGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 12,
  },
  topicBadge: {
    backgroundColor: '#FFE8E8',
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 20,
  },
  topicText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#FF5252',
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
  },
  infoText: {
    fontSize: 14,
    color: '#4A90A4',
    lineHeight: 20,
  },
  actions: {
    marginTop: 24,
  },
  saveButton: {
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
