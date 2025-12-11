/**
 * useChild Hook
 * Convenience hook for accessing child profile state and actions
 */

import { useCallback } from 'react';
import {
  useChildStore,
  useChildren,
  useActiveChild,
  useLearningProgress,
  useRecentSessions,
  useChildLoading,
  useChildError,
} from '../store/slices/childSlice';
import type {
  ChildProfile,
  ChildPreferences,
  LearningGoal,
  LearningSession,
  Achievement,
} from '../types';

// ============================================================================
// useChild Hook
// ============================================================================

export function useChild(childId?: string) {
  // State selectors
  const children = useChildren();
  const activeChild = useActiveChild();
  const learningProgress = useLearningProgress(childId);
  const recentSessions = useRecentSessions();
  const isLoading = useChildLoading();
  const error = useChildError();

  // Action selectors
  const addChild = useChildStore((state) => state.addChild);
  const updateChild = useChildStore((state) => state.updateChild);
  const removeChild = useChildStore((state) => state.removeChild);
  const setActiveChild = useChildStore((state) => state.setActiveChild);
  const updateChildPreferences = useChildStore((state) => state.updateChildPreferences);
  const addLearningGoal = useChildStore((state) => state.addLearningGoal);
  const updateLearningGoal = useChildStore((state) => state.updateLearningGoal);
  const removeLearningGoal = useChildStore((state) => state.removeLearningGoal);
  const fetchLearningProgress = useChildStore((state) => state.fetchLearningProgress);
  const fetchRecentSessions = useChildStore((state) => state.fetchRecentSessions);
  const fetchSessionDetails = useChildStore((state) => state.fetchSessionDetails);
  const fetchAchievements = useChildStore((state) => state.fetchAchievements);
  const pairDeviceToChild = useChildStore((state) => state.pairDeviceToChild);
  const unpairDeviceFromChild = useChildStore((state) => state.unpairDeviceFromChild);
  const clearError = useChildStore((state) => state.clearError);

  // ============================================================================
  // Wrapped Actions with Error Handling
  // ============================================================================

  const handleAddChild = useCallback(
    async (childData: Omit<ChildProfile, 'id' | 'createdAt' | 'updatedAt'>): Promise<boolean> => {
      try {
        await addChild(childData);
        return true;
      } catch (error) {
        console.error('Add child failed:', error);
        return false;
      }
    },
    [addChild]
  );

  const handleUpdateChild = useCallback(
    async (id: string, updates: Partial<ChildProfile>): Promise<boolean> => {
      try {
        await updateChild(id, updates);
        return true;
      } catch (error) {
        console.error('Update child failed:', error);
        return false;
      }
    },
    [updateChild]
  );

  const handleRemoveChild = useCallback(
    async (id: string): Promise<boolean> => {
      try {
        await removeChild(id);
        return true;
      } catch (error) {
        console.error('Remove child failed:', error);
        return false;
      }
    },
    [removeChild]
  );

  const handleUpdatePreferences = useCallback(
    async (id: string, preferences: Partial<ChildPreferences>): Promise<boolean> => {
      try {
        await updateChildPreferences(id, preferences);
        return true;
      } catch (error) {
        console.error('Update preferences failed:', error);
        return false;
      }
    },
    [updateChildPreferences]
  );

  const handleAddGoal = useCallback(
    async (
      id: string,
      goal: Omit<LearningGoal, 'id' | 'childId' | 'createdAt'>
    ): Promise<boolean> => {
      try {
        await addLearningGoal(id, goal);
        return true;
      } catch (error) {
        console.error('Add goal failed:', error);
        return false;
      }
    },
    [addLearningGoal]
  );

  const handleUpdateGoal = useCallback(
    async (goalId: string, updates: Partial<LearningGoal>): Promise<boolean> => {
      try {
        await updateLearningGoal(goalId, updates);
        return true;
      } catch (error) {
        console.error('Update goal failed:', error);
        return false;
      }
    },
    [updateLearningGoal]
  );

  const handleRemoveGoal = useCallback(
    async (goalId: string): Promise<boolean> => {
      try {
        await removeLearningGoal(goalId);
        return true;
      } catch (error) {
        console.error('Remove goal failed:', error);
        return false;
      }
    },
    [removeLearningGoal]
  );

  const handleFetchProgress = useCallback(
    async (id: string, period: 'daily' | 'weekly' | 'monthly' | 'all-time'): Promise<boolean> => {
      try {
        await fetchLearningProgress(id, period);
        return true;
      } catch (error) {
        console.error('Fetch progress failed:', error);
        return false;
      }
    },
    [fetchLearningProgress]
  );

  const handleFetchSessions = useCallback(
    async (id: string, limit?: number): Promise<boolean> => {
      try {
        await fetchRecentSessions(id, limit);
        return true;
      } catch (error) {
        console.error('Fetch sessions failed:', error);
        return false;
      }
    },
    [fetchRecentSessions]
  );

  const handleFetchSessionDetails = useCallback(
    async (sessionId: string): Promise<LearningSession | null> => {
      try {
        return await fetchSessionDetails(sessionId);
      } catch (error) {
        console.error('Fetch session details failed:', error);
        return null;
      }
    },
    [fetchSessionDetails]
  );

  const handleFetchAchievements = useCallback(
    async (id: string): Promise<Achievement[]> => {
      try {
        return await fetchAchievements(id);
      } catch (error) {
        console.error('Fetch achievements failed:', error);
        return [];
      }
    },
    [fetchAchievements]
  );

  const handlePairDevice = useCallback(
    async (id: string, deviceId: string): Promise<boolean> => {
      try {
        await pairDeviceToChild(id, deviceId);
        return true;
      } catch (error) {
        console.error('Pair device failed:', error);
        return false;
      }
    },
    [pairDeviceToChild]
  );

  const handleUnpairDevice = useCallback(
    async (id: string): Promise<boolean> => {
      try {
        await unpairDeviceFromChild(id);
        return true;
      } catch (error) {
        console.error('Unpair device failed:', error);
        return false;
      }
    },
    [unpairDeviceFromChild]
  );

  // ============================================================================
  // Utility Functions
  // ============================================================================

  const getChildById = useCallback(
    (id: string): ChildProfile | undefined => {
      return children.find((c) => c.id === id);
    },
    [children]
  );

  const getChildByDeviceId = useCallback(
    (deviceId: string): ChildProfile | undefined => {
      return children.find((c) => c.deviceId === deviceId);
    },
    [children]
  );

  const getActiveChildId = useCallback((): string | null => {
    return activeChild?.id || null;
  }, [activeChild]);

  const hasChildren = useCallback((): boolean => {
    return children.length > 0;
  }, [children]);

  const getChildCount = useCallback((): number => {
    return children.length;
  }, [children]);

  const getChildGoals = useCallback(
    (id: string): LearningGoal[] => {
      const child = children.find((c) => c.id === id);
      return child?.learningGoals || [];
    },
    [children]
  );

  const getActiveGoals = useCallback(
    (id: string): LearningGoal[] => {
      const goals = getChildGoals(id);
      return goals.filter((g) => g.status === 'active');
    },
    [getChildGoals]
  );

  const getCompletedGoals = useCallback(
    (id: string): LearningGoal[] => {
      const goals = getChildGoals(id);
      return goals.filter((g) => g.status === 'completed');
    },
    [getChildGoals]
  );

  const getTotalLearningTime = useCallback(
    (id: string): number => {
      return learningProgress?.totalDuration || 0;
    },
    [learningProgress]
  );

  const getAverageSessionLength = useCallback(
    (id: string): number => {
      return learningProgress?.averageSessionLength || 0;
    },
    [learningProgress]
  );

  const getTotalQuestions = useCallback(
    (id: string): number => {
      return learningProgress?.questionsAsked || 0;
    },
    [learningProgress]
  );

  const getTopicsExplored = useCallback(
    (id: string): string[] => {
      return learningProgress?.topicsExplored || [];
    },
    [learningProgress]
  );

  const hasDevicePaired = useCallback(
    (id: string): boolean => {
      const child = children.find((c) => c.id === id);
      return !!child?.deviceId;
    },
    [children]
  );

  const canAddMoreChildren = useCallback(
    (maxChildren: number = 5): boolean => {
      return children.length < maxChildren;
    },
    [children]
  );

  const getChildAge = useCallback(
    (id: string): number | undefined => {
      const child = children.find((c) => c.id === id);
      return child?.age;
    },
    [children]
  );

  const getChildGrade = useCallback(
    (id: string): string | undefined => {
      const child = children.find((c) => c.id === id);
      return child?.grade;
    },
    [children]
  );

  // ============================================================================
  // Return Hook API
  // ============================================================================

  return {
    // State
    children,
    activeChild,
    learningProgress,
    recentSessions,
    isLoading,
    error,

    // Actions
    addChild: handleAddChild,
    updateChild: handleUpdateChild,
    removeChild: handleRemoveChild,
    setActiveChild,
    updatePreferences: handleUpdatePreferences,
    addGoal: handleAddGoal,
    updateGoal: handleUpdateGoal,
    removeGoal: handleRemoveGoal,
    fetchProgress: handleFetchProgress,
    fetchSessions: handleFetchSessions,
    fetchSessionDetails: handleFetchSessionDetails,
    fetchAchievements: handleFetchAchievements,
    pairDevice: handlePairDevice,
    unpairDevice: handleUnpairDevice,
    clearError,

    // Utilities
    getChildById,
    getChildByDeviceId,
    getActiveChildId,
    hasChildren,
    getChildCount,
    getChildGoals,
    getActiveGoals,
    getCompletedGoals,
    getTotalLearningTime,
    getAverageSessionLength,
    getTotalQuestions,
    getTopicsExplored,
    hasDevicePaired,
    canAddMoreChildren,
    getChildAge,
    getChildGrade,
  };
}

export default useChild;
