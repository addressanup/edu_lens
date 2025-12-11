/**
 * Authentication context for EduLens Parent Companion App
 * Manages user authentication state and provides auth methods
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import type { ReactNode } from 'react';
import { childrenApi, type ChildProfile as ApiChildProfile, type ChildCreate } from '../services/api';

interface User {
  id: string;
  email: string;
  name: string;
  children: ChildProfile[];
}

interface ChildProfile {
  id: string;
  name: string;
  age: number;
  grade: string;
  language: string;  // Preferred language for tutoring (en, es, fr, de, zh, hi, ne)
  deviceId?: string;
}

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  addChild: (profile: Omit<ChildProfile, 'id'>) => Promise<void>;
  updateChild: (childId: string, updates: Partial<ChildProfile>) => Promise<void>;
  removeChild: (childId: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps): React.JSX.Element {
  const [state, setState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
  });

  // Check for existing session on mount
  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        // TODO: Implement actual session check with secure storage
        // const token = await SecureStorage.get('auth_token');
        // if (token) { ... validate and fetch user ... }
        setState(prev => ({ ...prev, isLoading: false }));
      } catch (error) {
        console.error('Auth check failed:', error);
        setState(prev => ({ ...prev, isLoading: false }));
      }
    };

    checkAuthStatus();
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setState(prev => ({ ...prev, isLoading: true }));
    try {
      // TODO: Implement actual auth API call
      // const response = await authService.login(email, password);
      // await SecureStorage.set('auth_token', response.token);

      // For now, create user and fetch children from backend
      const userId = '1'; // Would come from auth response

      // Fetch existing children from backend
      const childrenResponse = await childrenApi.list(userId);
      const children: ChildProfile[] = childrenResponse.success && childrenResponse.data
        ? childrenResponse.data.map(c => ({
            id: c.id,
            name: c.name,
            age: c.age,
            grade: c.grade,
            language: c.language || 'en',  // Include language, default to English
          }))
        : [];

      const user: User = {
        id: userId,
        email,
        name: 'Parent',
        children,
      };

      setState({
        user,
        isLoading: false,
        isAuthenticated: true,
      });
    } catch (error) {
      setState(prev => ({ ...prev, isLoading: false }));
      throw error;
    }
  }, []);

  const logout = useCallback(async () => {
    setState(prev => ({ ...prev, isLoading: true }));
    try {
      // TODO: Clear secure storage and invalidate session
      // await SecureStorage.remove('auth_token');
      // await authService.logout();

      setState({
        user: null,
        isLoading: false,
        isAuthenticated: false,
      });
    } catch (error) {
      setState(prev => ({ ...prev, isLoading: false }));
      throw error;
    }
  }, []);

  const register = useCallback(async (email: string, password: string, name: string) => {
    setState(prev => ({ ...prev, isLoading: true }));
    try {
      // TODO: Implement actual registration
      // Must include COPPA-compliant parental consent flow
      throw new Error('Registration not yet implemented');
    } catch (error) {
      setState(prev => ({ ...prev, isLoading: false }));
      throw error;
    }
  }, []);

  const resetPassword = useCallback(async (email: string) => {
    // TODO: Implement password reset
    throw new Error('Password reset not yet implemented');
  }, []);

  const addChild = useCallback(async (profile: Omit<ChildProfile, 'id'>) => {
    if (!state.user) throw new Error('Not authenticated');

    // Call the backend API to create child profile
    const createData: ChildCreate = {
      name: profile.name,
      age: profile.age,
      grade: profile.grade,
      language: profile.language || 'en',  // Use profile language or default to English
      parent_id: state.user.id,
    };

    const response = await childrenApi.create(createData);

    if (response.success && response.data) {
      const newChild: ChildProfile = {
        id: response.data.id,
        name: response.data.name,
        age: response.data.age,
        grade: response.data.grade,
        language: response.data.language || profile.language || 'en',  // Include language
        deviceId: profile.deviceId,
      };

      setState(prev => ({
        ...prev,
        user: prev.user ? {
          ...prev.user,
          children: [...prev.user.children, newChild],
        } : null,
      }));
    } else {
      throw new Error(response.error?.message || 'Failed to add child');
    }
  }, [state.user]);

  const updateChild = useCallback(async (childId: string, updates: Partial<ChildProfile>) => {
    if (!state.user) throw new Error('Not authenticated');

    // Call the backend API to update child profile
    const response = await childrenApi.update(childId, {
      name: updates.name,
      age: updates.age,
      grade: updates.grade,
      language: updates.language,  // Include language updates
    });

    if (response.success && response.data) {
      setState(prev => ({
        ...prev,
        user: prev.user ? {
          ...prev.user,
          children: prev.user.children.map(child =>
            child.id === childId ? { ...child, ...updates } : child
          ),
        } : null,
      }));
    } else {
      throw new Error(response.error?.message || 'Failed to update child');
    }
  }, [state.user]);

  const removeChild = useCallback(async (childId: string) => {
    if (!state.user) throw new Error('Not authenticated');

    // Call the backend API to delete child profile (COPPA compliant)
    const response = await childrenApi.delete(childId);

    if (response.success) {
      setState(prev => ({
        ...prev,
        user: prev.user ? {
          ...prev.user,
          children: prev.user.children.filter(child => child.id !== childId),
        } : null,
      }));
    } else {
      throw new Error(response.error?.message || 'Failed to remove child');
    }
  }, [state.user]);

  const value: AuthContextType = {
    ...state,
    login,
    logout,
    register,
    resetPassword,
    addChild,
    updateChild,
    removeChild,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
