/**
 * Authentication State Slice
 * Manages user authentication state, login/logout, and token management
 * Using Zustand for clean, minimal boilerplate state management
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import * as SecureStore from 'expo-secure-store';
import type {
  AuthState,
  User,
  AuthTokens,
  LoginCredentials,
  RegisterData,
} from '../../types';

// ============================================================================
// Secure Storage Adapter for Zustand Persist
// ============================================================================

const secureStorage = {
  getItem: async (name: string): Promise<string | null> => {
    try {
      return await SecureStore.getItemAsync(name);
    } catch (error) {
      console.error('SecureStore getItem error:', error);
      return null;
    }
  },
  setItem: async (name: string, value: string): Promise<void> => {
    try {
      await SecureStore.setItemAsync(name, value);
    } catch (error) {
      console.error('SecureStore setItem error:', error);
    }
  },
  removeItem: async (name: string): Promise<void> => {
    try {
      await SecureStore.deleteItemAsync(name);
    } catch (error) {
      console.error('SecureStore removeItem error:', error);
    }
  },
};

// ============================================================================
// Auth Slice Interface
// ============================================================================

interface AuthSlice extends AuthState {
  // Actions
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  refreshToken: () => Promise<void>;
  updateUser: (updates: Partial<User>) => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;

  // Token management
  setTokens: (tokens: AuthTokens) => void;
  clearTokens: () => void;

  // State setters
  setUser: (user: User | null) => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;

  // Session management
  checkAuthStatus: () => Promise<boolean>;
  isTokenExpired: () => boolean;
}

// ============================================================================
// Auth Store Implementation
// ============================================================================

export const useAuthStore = create<AuthSlice>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      tokens: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // ========================================================================
      // Login
      // ========================================================================
      login: async (credentials: LoginCredentials) => {
        set({ isLoading: true, error: null });

        try {
          // Import API service dynamically to avoid circular dependencies
          const { apiService } = await import('../../services/api');

          const response = await apiService.post<{
            user: User;
            tokens: AuthTokens;
          }>('/auth/login', credentials);

          if (response.success && response.data) {
            const { user, tokens } = response.data;

            set({
              user,
              tokens,
              isAuthenticated: true,
              isLoading: false,
              error: null,
            });

            // Store tokens securely
            await SecureStore.setItemAsync('auth_tokens', JSON.stringify(tokens));
          } else {
            throw new Error(response.error?.message || 'Login failed');
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Login failed';
          set({
            isLoading: false,
            error: errorMessage,
            isAuthenticated: false,
          });
          throw error;
        }
      },

      // ========================================================================
      // Logout
      // ========================================================================
      logout: async () => {
        set({ isLoading: true });

        try {
          const { apiService } = await import('../../services/api');

          // Call logout endpoint to invalidate tokens on server
          await apiService.post('/auth/logout');
        } catch (error) {
          console.error('Logout API call failed:', error);
          // Continue with local logout even if API call fails
        } finally {
          // Clear local state and secure storage
          set({
            user: null,
            tokens: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,
          });

          await SecureStore.deleteItemAsync('auth_tokens');
        }
      },

      // ========================================================================
      // Register
      // ========================================================================
      register: async (data: RegisterData) => {
        set({ isLoading: true, error: null });

        try {
          const { apiService } = await import('../../services/api');

          // Validate COPPA compliance
          if (!data.parentalConsent) {
            throw new Error('Parental consent is required for registration');
          }

          const response = await apiService.post<{
            user: User;
            tokens: AuthTokens;
          }>('/auth/register', data);

          if (response.success && response.data) {
            const { user, tokens } = response.data;

            set({
              user,
              tokens,
              isAuthenticated: true,
              isLoading: false,
              error: null,
            });

            await SecureStore.setItemAsync('auth_tokens', JSON.stringify(tokens));
          } else {
            throw new Error(response.error?.message || 'Registration failed');
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Registration failed';
          set({
            isLoading: false,
            error: errorMessage,
          });
          throw error;
        }
      },

      // ========================================================================
      // Refresh Token
      // ========================================================================
      refreshToken: async () => {
        const { tokens } = get();

        if (!tokens?.refreshToken) {
          throw new Error('No refresh token available');
        }

        try {
          const { apiService } = await import('../../services/api');

          const response = await apiService.post<{
            tokens: AuthTokens;
          }>('/auth/refresh', {
            refreshToken: tokens.refreshToken,
          });

          if (response.success && response.data) {
            const newTokens = response.data.tokens;

            set({ tokens: newTokens });
            await SecureStore.setItemAsync('auth_tokens', JSON.stringify(newTokens));
          } else {
            throw new Error('Token refresh failed');
          }
        } catch (error) {
          // If refresh fails, log out the user
          await get().logout();
          throw error;
        }
      },

      // ========================================================================
      // Update User Profile
      // ========================================================================
      updateUser: async (updates: Partial<User>) => {
        const { user } = get();

        if (!user) {
          throw new Error('No user logged in');
        }

        set({ isLoading: true, error: null });

        try {
          const { apiService } = await import('../../services/api');

          const response = await apiService.patch<{ user: User }>(
            `/users/${user.id}`,
            updates
          );

          if (response.success && response.data) {
            set({
              user: response.data.user,
              isLoading: false,
            });
          } else {
            throw new Error('Failed to update user profile');
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Update failed';
          set({
            isLoading: false,
            error: errorMessage,
          });
          throw error;
        }
      },

      // ========================================================================
      // Reset Password
      // ========================================================================
      resetPassword: async (email: string) => {
        set({ isLoading: true, error: null });

        try {
          const { apiService } = await import('../../services/api');

          await apiService.post('/auth/reset-password', { email });

          set({ isLoading: false });
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Password reset failed';
          set({
            isLoading: false,
            error: errorMessage,
          });
          throw error;
        }
      },

      // ========================================================================
      // Change Password
      // ========================================================================
      changePassword: async (currentPassword: string, newPassword: string) => {
        set({ isLoading: true, error: null });

        try {
          const { apiService } = await import('../../services/api');

          await apiService.post('/auth/change-password', {
            currentPassword,
            newPassword,
          });

          set({ isLoading: false });
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Password change failed';
          set({
            isLoading: false,
            error: errorMessage,
          });
          throw error;
        }
      },

      // ========================================================================
      // Token Management
      // ========================================================================
      setTokens: (tokens: AuthTokens) => {
        set({ tokens });
      },

      clearTokens: () => {
        set({ tokens: null });
      },

      // ========================================================================
      // State Setters
      // ========================================================================
      setUser: (user: User | null) => {
        set({ user, isAuthenticated: !!user });
      },

      setLoading: (isLoading: boolean) => {
        set({ isLoading });
      },

      setError: (error: string | null) => {
        set({ error });
      },

      clearError: () => {
        set({ error: null });
      },

      // ========================================================================
      // Session Management
      // ========================================================================
      checkAuthStatus: async (): Promise<boolean> => {
        try {
          const storedTokens = await SecureStore.getItemAsync('auth_tokens');

          if (!storedTokens) {
            return false;
          }

          const tokens: AuthTokens = JSON.parse(storedTokens);

          // Check if token is expired
          const expiresAt = new Date(tokens.expiresAt);
          const now = new Date();

          if (expiresAt <= now) {
            // Try to refresh token
            set({ tokens });
            await get().refreshToken();
            return true;
          }

          // Token is valid, restore session
          const { apiService } = await import('../../services/api');
          const response = await apiService.get<{ user: User }>('/auth/me');

          if (response.success && response.data) {
            set({
              user: response.data.user,
              tokens,
              isAuthenticated: true,
            });
            return true;
          }

          return false;
        } catch (error) {
          console.error('Auth status check failed:', error);
          return false;
        }
      },

      isTokenExpired: (): boolean => {
        const { tokens } = get();

        if (!tokens) return true;

        const expiresAt = new Date(tokens.expiresAt);
        const now = new Date();

        // Consider token expired if it expires in less than 5 minutes
        const bufferTime = 5 * 60 * 1000; // 5 minutes in milliseconds

        return expiresAt.getTime() - now.getTime() < bufferTime;
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => secureStorage),
      // Only persist essential data
      partialize: (state) => ({
        user: state.user,
        tokens: state.tokens,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

// ============================================================================
// Selector Hooks (for performance optimization)
// ============================================================================

export const useUser = () => useAuthStore((state) => state.user);
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated);
export const useAuthLoading = () => useAuthStore((state) => state.isLoading);
export const useAuthError = () => useAuthStore((state) => state.error);
