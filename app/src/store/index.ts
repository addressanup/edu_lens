/**
 * Store Configuration
 * Central export for all Zustand stores and state management
 */

// ============================================================================
// Store Exports
// ============================================================================

// Auth Store
export {
  useAuthStore,
  useUser,
  useIsAuthenticated,
  useAuthLoading,
  useAuthError,
} from './slices/authSlice';

// Device Store
export {
  useDeviceStore,
  useDevices,
  useConnectedDevice,
  useDiscoveredDevices,
  useIsScanning,
  useDeviceError,
} from './slices/deviceSlice';

// Child Store
export {
  useChildStore,
  useChildren,
  useActiveChild,
  useLearningProgress,
  useRecentSessions,
  useChildLoading,
  useChildError,
} from './slices/childSlice';

// ============================================================================
// Combined Store Actions
// ============================================================================

/**
 * Initialize all stores
 * Call this on app startup to restore persisted state and check auth status
 */
export const initializeStores = async (): Promise<void> => {
  try {
    console.log('Initializing stores...');

    // Import stores dynamically
    const { useAuthStore } = await import('./slices/authSlice');
    const { useDeviceStore } = await import('./slices/deviceSlice');

    // Check authentication status
    const isAuthenticated = await useAuthStore.getState().checkAuthStatus();

    if (isAuthenticated) {
      console.log('User authenticated - loading data...');

      // Initialize device Bluetooth status
      const bluetoothEnabled = await (await import('../services/bluetooth'))
        .bluetoothService.isBluetoothEnabled();

      useDeviceStore.getState().setBluetoothEnabled(bluetoothEnabled);
    }

    console.log('Stores initialized successfully');
  } catch (error) {
    console.error('Store initialization failed:', error);
  }
};

/**
 * Reset all stores
 * Call this when user logs out to clear all state
 */
export const resetAllStores = async (): Promise<void> => {
  try {
    console.log('Resetting all stores...');

    const { useAuthStore } = await import('./slices/authSlice');
    const { useDeviceStore } = await import('./slices/deviceSlice');
    const { useChildStore } = await import('./slices/childSlice');

    // Logout will clear auth store
    await useAuthStore.getState().logout();

    // Reset device store
    useDeviceStore.setState({
      devices: [],
      connectedDevice: null,
      discoveredDevices: [],
      isScanning: false,
      error: null,
    });

    // Reset child store
    useChildStore.setState({
      children: [],
      activeChild: null,
      learningProgress: {},
      recentSessions: [],
      isLoading: false,
      error: null,
    });

    // Disconnect all Bluetooth devices
    const { bluetoothService } = await import('../services/bluetooth');
    await bluetoothService.destroy();

    console.log('All stores reset successfully');
  } catch (error) {
    console.error('Failed to reset stores:', error);
  }
};

/**
 * Sync data with backend
 * Call this periodically to ensure data is up to date
 */
export const syncStoreData = async (): Promise<void> => {
  try {
    console.log('Syncing store data...');

    const { useAuthStore } = await import('./slices/authSlice');
    const { useChildStore } = await import('./slices/childSlice');
    const { useDeviceStore } = await import('./slices/deviceSlice');

    // Only sync if authenticated
    if (!useAuthStore.getState().isAuthenticated) {
      return;
    }

    // Refresh user data
    const { apiService } = await import('../services/api');
    const userResponse = await apiService.get('/auth/me');

    if (userResponse.success && userResponse.data) {
      useAuthStore.getState().setUser(userResponse.data.user);
    }

    // Refresh children data
    const childrenResponse = await apiService.get('/children');

    if (childrenResponse.success && childrenResponse.data) {
      const children = childrenResponse.data.children;

      children.forEach((child: any) => {
        const existingChild = useChildStore
          .getState()
          .children.find((c) => c.id === child.id);

        if (existingChild) {
          useChildStore.getState().updateChild(child.id, child);
        } else {
          useChildStore.setState((state) => ({
            children: [...state.children, child],
          }));
        }
      });
    }

    // Refresh device data
    const devicesResponse = await apiService.get('/devices');

    if (devicesResponse.success && devicesResponse.data) {
      const devices = devicesResponse.data.devices;

      devices.forEach((device: any) => {
        useDeviceStore.getState().addDevice(device);
      });
    }

    console.log('Store data synced successfully');
  } catch (error) {
    console.error('Failed to sync store data:', error);
  }
};

/**
 * Get global loading state
 * Returns true if any store is currently loading
 */
export const useGlobalLoading = (): boolean => {
  const { useAuthStore } = require('./slices/authSlice');
  const { useChildStore } = require('./slices/childSlice');

  const authLoading = useAuthStore((state: any) => state.isLoading);
  const childLoading = useChildStore((state: any) => state.isLoading);

  return authLoading || childLoading;
};

/**
 * Get global error state
 * Returns first error found across all stores
 */
export const useGlobalError = (): string | null => {
  const { useAuthStore } = require('./slices/authSlice');
  const { useDeviceStore } = require('./slices/deviceSlice');
  const { useChildStore } = require('./slices/childSlice');

  const authError = useAuthStore((state: any) => state.error);
  const deviceError = useDeviceStore((state: any) => state.error);
  const childError = useChildStore((state: any) => state.error);

  return authError || deviceError || childError;
};

/**
 * Clear all errors
 */
export const clearAllErrors = async (): Promise<void> => {
  const { useAuthStore } = await import('./slices/authSlice');
  const { useDeviceStore } = await import('./slices/deviceSlice');
  const { useChildStore } = await import('./slices/childSlice');

  useAuthStore.getState().clearError();
  useDeviceStore.getState().clearError();
  useChildStore.getState().clearError();
};

// ============================================================================
// Type Exports
// ============================================================================

export type {
  // Auth types
  User,
  AuthTokens,
  LoginCredentials,
  RegisterData,
  // Device types
  EduLensDevice,
  DeviceCommand,
  DeviceSettings,
  DeviceStatus,
  BluetoothScanResult,
  // Child types
  ChildProfile,
  ChildPreferences,
  LearningGoal,
  LearningProgress,
  LearningSession,
  Achievement,
  // API types
  ApiResponse,
  ApiError,
} from '../types';

// ============================================================================
// Dev Tools (Development Only)
// ============================================================================

if (__DEV__) {
  // Expose stores to global scope for debugging
  (global as any).__EDULENS_STORES__ = {
    getAuthState: async () => (await import('./slices/authSlice')).useAuthStore.getState(),
    getDeviceState: async () => (await import('./slices/deviceSlice')).useDeviceStore.getState(),
    getChildState: async () => (await import('./slices/childSlice')).useChildStore.getState(),
  };

  console.log('Dev tools enabled: Access stores via __EDULENS_STORES__');
}
