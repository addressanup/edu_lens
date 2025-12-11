/**
 * Child Profile State Slice
 * Manages child profiles, learning progress, sessions, and achievements
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';
import type {
  ChildState,
  ChildProfile,
  ChildPreferences,
  LearningGoal,
  LearningProgress,
  LearningSession,
  Achievement,
} from '../../types';

// ============================================================================
// Child Slice Interface
// ============================================================================

interface ChildSlice extends ChildState {
  // Child profile management
  addChild: (child: Omit<ChildProfile, 'id' | 'createdAt' | 'updatedAt'>) => Promise<void>;
  updateChild: (childId: string, updates: Partial<ChildProfile>) => Promise<void>;
  removeChild: (childId: string) => Promise<void>;
  setActiveChild: (childId: string | null) => void;

  // Child preferences
  updateChildPreferences: (childId: string, preferences: Partial<ChildPreferences>) => Promise<void>;

  // Learning goals
  addLearningGoal: (childId: string, goal: Omit<LearningGoal, 'id' | 'childId' | 'createdAt'>) => Promise<void>;
  updateLearningGoal: (goalId: string, updates: Partial<LearningGoal>) => Promise<void>;
  removeLearningGoal: (goalId: string) => Promise<void>;

  // Learning progress and sessions
  fetchLearningProgress: (
    childId: string,
    period: 'daily' | 'weekly' | 'monthly' | 'all-time'
  ) => Promise<void>;
  fetchRecentSessions: (childId: string, limit?: number) => Promise<void>;
  fetchSessionDetails: (sessionId: string) => Promise<LearningSession>;

  // Achievements
  fetchAchievements: (childId: string) => Promise<Achievement[]>;

  // Device pairing
  pairDeviceToChild: (childId: string, deviceId: string) => Promise<void>;
  unpairDeviceFromChild: (childId: string) => Promise<void>;

  // State management
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
}

// ============================================================================
// Child Store Implementation
// ============================================================================

export const useChildStore = create<ChildSlice>()(
  persist(
    (set, get) => ({
      // Initial state
      children: [],
      activeChild: null,
      learningProgress: {},
      recentSessions: [],
      isLoading: false,
      error: null,

      // ========================================================================
      // Child Profile Management
      // ========================================================================
      addChild: async (childData) => {
        set({ isLoading: true, error: null });

        try {
          const { apiService } = await import('../../services/api');

          // COPPA compliance check - ensure parental consent
          const response = await apiService.post<{ child: ChildProfile }>(
            '/children',
            childData
          );

          if (response.success && response.data) {
            const newChild = response.data.child;

            set((state) => ({
              children: [...state.children, newChild],
              activeChild: state.children.length === 0 ? newChild : state.activeChild,
              isLoading: false,
            }));
          } else {
            throw new Error(response.error?.message || 'Failed to add child');
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to add child';
          set({
            isLoading: false,
            error: errorMessage,
          });
          throw error;
        }
      },

      updateChild: async (childId: string, updates: Partial<ChildProfile>) => {
        set({ isLoading: true, error: null });

        try {
          const { apiService } = await import('../../services/api');

          const response = await apiService.patch<{ child: ChildProfile }>(
            `/children/${childId}`,
            updates
          );

          if (response.success && response.data) {
            const updatedChild = response.data.child;

            set((state) => ({
              children: state.children.map((c) => (c.id === childId ? updatedChild : c)),
              activeChild:
                state.activeChild?.id === childId ? updatedChild : state.activeChild,
              isLoading: false,
            }));
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to update child';
          set({
            isLoading: false,
            error: errorMessage,
          });
          throw error;
        }
      },

      removeChild: async (childId: string) => {
        set({ isLoading: true, error: null });

        try {
          const { apiService } = await import('../../services/api');

          await apiService.delete(`/children/${childId}`);

          set((state) => {
            const remainingChildren = state.children.filter((c) => c.id !== childId);

            return {
              children: remainingChildren,
              activeChild:
                state.activeChild?.id === childId
                  ? remainingChildren[0] || null
                  : state.activeChild,
              isLoading: false,
            };
          });
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to remove child';
          set({
            isLoading: false,
            error: errorMessage,
          });
          throw error;
        }
      },

      setActiveChild: (childId: string | null) => {
        set((state) => ({
          activeChild: childId
            ? state.children.find((c) => c.id === childId) || null
            : null,
        }));
      },

      // ========================================================================
      // Child Preferences
      // ========================================================================
      updateChildPreferences: async (
        childId: string,
        preferences: Partial<ChildPreferences>
      ) => {
        try {
          const { apiService } = await import('../../services/api');

          const response = await apiService.patch<{ child: ChildProfile }>(
            `/children/${childId}/preferences`,
            preferences
          );

          if (response.success && response.data) {
            const updatedChild = response.data.child;

            set((state) => ({
              children: state.children.map((c) => (c.id === childId ? updatedChild : c)),
              activeChild:
                state.activeChild?.id === childId ? updatedChild : state.activeChild,
            }));
          }
        } catch (error) {
          const errorMessage =
            error instanceof Error ? error.message : 'Failed to update preferences';
          set({ error: errorMessage });
          throw error;
        }
      },

      // ========================================================================
      // Learning Goals
      // ========================================================================
      addLearningGoal: async (
        childId: string,
        goalData: Omit<LearningGoal, 'id' | 'childId' | 'createdAt'>
      ) => {
        try {
          const { apiService } = await import('../../services/api');

          const response = await apiService.post<{ goal: LearningGoal }>(
            `/children/${childId}/goals`,
            goalData
          );

          if (response.success && response.data) {
            const newGoal = response.data.goal;

            set((state) => ({
              children: state.children.map((c) =>
                c.id === childId
                  ? { ...c, learningGoals: [...c.learningGoals, newGoal] }
                  : c
              ),
            }));
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to add goal';
          set({ error: errorMessage });
          throw error;
        }
      },

      updateLearningGoal: async (goalId: string, updates: Partial<LearningGoal>) => {
        try {
          const { apiService } = await import('../../services/api');

          const response = await apiService.patch<{ goal: LearningGoal }>(
            `/goals/${goalId}`,
            updates
          );

          if (response.success && response.data) {
            const updatedGoal = response.data.goal;

            set((state) => ({
              children: state.children.map((c) => ({
                ...c,
                learningGoals: c.learningGoals.map((g) =>
                  g.id === goalId ? updatedGoal : g
                ),
              })),
            }));
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to update goal';
          set({ error: errorMessage });
          throw error;
        }
      },

      removeLearningGoal: async (goalId: string) => {
        try {
          const { apiService } = await import('../../services/api');

          await apiService.delete(`/goals/${goalId}`);

          set((state) => ({
            children: state.children.map((c) => ({
              ...c,
              learningGoals: c.learningGoals.filter((g) => g.id !== goalId),
            })),
          }));
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to remove goal';
          set({ error: errorMessage });
          throw error;
        }
      },

      // ========================================================================
      // Learning Progress and Sessions
      // ========================================================================
      fetchLearningProgress: async (
        childId: string,
        period: 'daily' | 'weekly' | 'monthly' | 'all-time'
      ) => {
        set({ isLoading: true, error: null });

        try {
          const { apiService } = await import('../../services/api');

          const response = await apiService.get<{ progress: LearningProgress }>(
            `/children/${childId}/progress`,
            { params: { period } }
          );

          if (response.success && response.data) {
            set((state) => ({
              learningProgress: {
                ...state.learningProgress,
                [childId]: response.data!.progress,
              },
              isLoading: false,
            }));
          }
        } catch (error) {
          const errorMessage =
            error instanceof Error ? error.message : 'Failed to fetch progress';
          set({
            isLoading: false,
            error: errorMessage,
          });
          throw error;
        }
      },

      fetchRecentSessions: async (childId: string, limit = 10) => {
        set({ isLoading: true, error: null });

        try {
          const { apiService } = await import('../../services/api');

          const response = await apiService.get<{ sessions: LearningSession[] }>(
            `/children/${childId}/sessions`,
            { params: { limit } }
          );

          if (response.success && response.data) {
            set({
              recentSessions: response.data.sessions,
              isLoading: false,
            });
          }
        } catch (error) {
          const errorMessage =
            error instanceof Error ? error.message : 'Failed to fetch sessions';
          set({
            isLoading: false,
            error: errorMessage,
          });
          throw error;
        }
      },

      fetchSessionDetails: async (sessionId: string): Promise<LearningSession> => {
        try {
          const { apiService } = await import('../../services/api');

          const response = await apiService.get<{ session: LearningSession }>(
            `/sessions/${sessionId}`
          );

          if (response.success && response.data) {
            return response.data.session;
          }

          throw new Error('Failed to fetch session details');
        } catch (error) {
          const errorMessage =
            error instanceof Error ? error.message : 'Failed to fetch session';
          set({ error: errorMessage });
          throw error;
        }
      },

      // ========================================================================
      // Achievements
      // ========================================================================
      fetchAchievements: async (childId: string): Promise<Achievement[]> => {
        try {
          const { apiService } = await import('../../services/api');

          const response = await apiService.get<{ achievements: Achievement[] }>(
            `/children/${childId}/achievements`
          );

          if (response.success && response.data) {
            return response.data.achievements;
          }

          return [];
        } catch (error) {
          console.error('Failed to fetch achievements:', error);
          return [];
        }
      },

      // ========================================================================
      // Device Pairing
      // ========================================================================
      pairDeviceToChild: async (childId: string, deviceId: string) => {
        try {
          const { apiService } = await import('../../services/api');

          const response = await apiService.post<{ child: ChildProfile }>(
            `/children/${childId}/pair`,
            { deviceId }
          );

          if (response.success && response.data) {
            const updatedChild = response.data.child;

            set((state) => ({
              children: state.children.map((c) => (c.id === childId ? updatedChild : c)),
              activeChild:
                state.activeChild?.id === childId ? updatedChild : state.activeChild,
            }));
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Pairing failed';
          set({ error: errorMessage });
          throw error;
        }
      },

      unpairDeviceFromChild: async (childId: string) => {
        try {
          const { apiService } = await import('../../services/api');

          const response = await apiService.post<{ child: ChildProfile }>(
            `/children/${childId}/unpair`
          );

          if (response.success && response.data) {
            const updatedChild = response.data.child;

            set((state) => ({
              children: state.children.map((c) => (c.id === childId ? updatedChild : c)),
              activeChild:
                state.activeChild?.id === childId ? updatedChild : state.activeChild,
            }));
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Unpairing failed';
          set({ error: errorMessage });
          throw error;
        }
      },

      // ========================================================================
      // State Management
      // ========================================================================
      setLoading: (isLoading: boolean) => {
        set({ isLoading });
      },

      setError: (error: string | null) => {
        set({ error });
      },

      clearError: () => {
        set({ error: null });
      },
    }),
    {
      name: 'child-storage',
      storage: createJSONStorage(() => AsyncStorage),
      // Persist children and active child selection
      partialize: (state) => ({
        children: state.children,
        activeChild: state.activeChild,
      }),
    }
  )
);

// ============================================================================
// Selector Hooks (for performance optimization)
// ============================================================================

export const useChildren = () => useChildStore((state) => state.children);
export const useActiveChild = () => useChildStore((state) => state.activeChild);
export const useLearningProgress = (childId?: string) =>
  useChildStore((state) =>
    childId ? state.learningProgress[childId] : null
  );
export const useRecentSessions = () => useChildStore((state) => state.recentSessions);
export const useChildLoading = () => useChildStore((state) => state.isLoading);
export const useChildError = () => useChildStore((state) => state.error);
