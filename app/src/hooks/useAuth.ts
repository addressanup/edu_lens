/**
 * useAuth Hook
 * Convenience hook for accessing authentication state and actions
 */

import { useCallback } from 'react';
import {
  useAuthStore,
  useUser,
  useIsAuthenticated,
  useAuthLoading,
  useAuthError,
} from '../store/slices/authSlice';
import type { LoginCredentials, RegisterData, User } from '../types';

// ============================================================================
// useAuth Hook
// ============================================================================

export function useAuth() {
  // State selectors
  const user = useUser();
  const isAuthenticated = useIsAuthenticated();
  const isLoading = useAuthLoading();
  const error = useAuthError();

  // Action selectors
  const login = useAuthStore((state) => state.login);
  const logout = useAuthStore((state) => state.logout);
  const register = useAuthStore((state) => state.register);
  const updateUser = useAuthStore((state) => state.updateUser);
  const resetPassword = useAuthStore((state) => state.resetPassword);
  const changePassword = useAuthStore((state) => state.changePassword);
  const clearError = useAuthStore((state) => state.clearError);

  // ============================================================================
  // Wrapped Actions with Error Handling
  // ============================================================================

  const handleLogin = useCallback(
    async (credentials: LoginCredentials): Promise<boolean> => {
      try {
        await login(credentials);
        return true;
      } catch (error) {
        console.error('Login failed:', error);
        return false;
      }
    },
    [login]
  );

  const handleLogout = useCallback(async (): Promise<void> => {
    try {
      await logout();
    } catch (error) {
      console.error('Logout failed:', error);
    }
  }, [logout]);

  const handleRegister = useCallback(
    async (data: RegisterData): Promise<boolean> => {
      try {
        await register(data);
        return true;
      } catch (error) {
        console.error('Registration failed:', error);
        return false;
      }
    },
    [register]
  );

  const handleUpdateProfile = useCallback(
    async (updates: Partial<User>): Promise<boolean> => {
      try {
        await updateUser(updates);
        return true;
      } catch (error) {
        console.error('Profile update failed:', error);
        return false;
      }
    },
    [updateUser]
  );

  const handleResetPassword = useCallback(
    async (email: string): Promise<boolean> => {
      try {
        await resetPassword(email);
        return true;
      } catch (error) {
        console.error('Password reset failed:', error);
        return false;
      }
    },
    [resetPassword]
  );

  const handleChangePassword = useCallback(
    async (currentPassword: string, newPassword: string): Promise<boolean> => {
      try {
        await changePassword(currentPassword, newPassword);
        return true;
      } catch (error) {
        console.error('Password change failed:', error);
        return false;
      }
    },
    [changePassword]
  );

  // ============================================================================
  // Utility Functions
  // ============================================================================

  const hasPermission = useCallback(
    (permission: string): boolean => {
      // Implement permission checking logic based on user role/subscription
      if (!user) return false;

      // Example: Check subscription level for premium features
      if (permission === 'premium') {
        return user.subscription?.plan === 'premium' || user.subscription?.plan === 'family';
      }

      return true;
    },
    [user]
  );

  const isSubscriptionActive = useCallback((): boolean => {
    if (!user?.subscription) return false;

    return user.subscription.status === 'active' || user.subscription.status === 'trial';
  }, [user]);

  // ============================================================================
  // Return Hook API
  // ============================================================================

  return {
    // State
    user,
    isAuthenticated,
    isLoading,
    error,

    // Actions
    login: handleLogin,
    logout: handleLogout,
    register: handleRegister,
    updateProfile: handleUpdateProfile,
    resetPassword: handleResetPassword,
    changePassword: handleChangePassword,
    clearError,

    // Utilities
    hasPermission,
    isSubscriptionActive,
  };
}

export default useAuth;
