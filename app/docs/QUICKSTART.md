# EduLens Companion App - Quick Start Guide

## Installation Complete

The React Native architecture has been successfully set up with the following structure:

## What Was Created

### 1. Type Definitions (`/src/types/index.ts`)
Comprehensive TypeScript types for:
- User authentication and profiles
- Child profiles and learning data
- Device management and settings
- Learning analytics and sessions
- API request/response structures
- Bluetooth communication

### 2. State Management (Zustand)

#### Auth Slice (`/src/store/slices/authSlice.ts`)
- User authentication state
- Login/logout/register actions
- Token management with auto-refresh
- Secure token storage (Expo SecureStore)
- Session persistence

#### Device Slice (`/src/store/slices/deviceSlice.ts`)
- Device list and connection state
- Bluetooth scanning
- Device pairing and commands
- Settings management
- Firmware updates

#### Child Slice (`/src/store/slices/childSlice.ts`)
- Child profile management
- Learning progress tracking
- Goal management
- Session history
- Achievement tracking

#### Store Index (`/src/store/index.ts`)
- Centralized store exports
- Store initialization utilities
- Global state helpers
- Dev tools integration

### 3. Services

#### API Service (`/src/services/api.ts`)
- Axios-based HTTP client
- Automatic token injection
- Token refresh interceptor
- Error handling
- Request ID tracking
- Type-safe responses

#### Bluetooth Service (`/src/services/bluetooth.ts`)
- BLE device scanning
- Connection management
- Command/response handling
- Notification subscriptions
- Battery monitoring
- Status updates

### 4. Custom Hooks

#### useAuth (`/src/hooks/useAuth.ts`)
```typescript
const {
  user,
  isAuthenticated,
  login,
  logout,
  register,
  updateProfile
} = useAuth();
```

#### useDevice (`/src/hooks/useDevice.ts`)
```typescript
const {
  devices,
  connectedDevice,
  connect,
  disconnect,
  sendCommand,
  setVolume
} = useDevice();
```

#### useChild (`/src/hooks/useChild.ts`)
```typescript
const {
  children,
  activeChild,
  learningProgress,
  addChild,
  updateChild,
  fetchProgress
} = useChild();
```

## Usage Examples

### 1. Authentication

```typescript
import { useAuth } from '../hooks/useAuth';

function LoginScreen() {
  const { login, isLoading, error } = useAuth();

  const handleLogin = async () => {
    const success = await login({
      email: 'parent@example.com',
      password: 'password123'
    });

    if (success) {
      // Navigate to dashboard
    }
  };

  return (
    // UI implementation
  );
}
```

### 2. Device Connection

```typescript
import { useDevice } from '../hooks/useDevice';

function DeviceListScreen() {
  const {
    discoveredDevices,
    startScan,
    connect,
    isScanning
  } = useDevice();

  useEffect(() => {
    startScan();
  }, []);

  const handleConnect = async (deviceId: string) => {
    const success = await connect(deviceId);
    if (success) {
      // Show success message
    }
  };

  return (
    // Render device list
  );
}
```

### 3. Child Profile Management

```typescript
import { useChild } from '../hooks/useChild';

function ChildProfileScreen() {
  const {
    children,
    activeChild,
    learningProgress,
    fetchProgress
  } = useChild();

  useEffect(() => {
    if (activeChild) {
      fetchProgress(activeChild.id, 'weekly');
    }
  }, [activeChild]);

  return (
    // Display child stats
  );
}
```

### 4. Direct Store Access (Advanced)

```typescript
import { useAuthStore, useDeviceStore } from '../store';

function AdvancedScreen() {
  // Access specific state slices
  const user = useAuthStore((state) => state.user);
  const devices = useDeviceStore((state) => state.devices);

  // Access actions directly
  const logout = useAuthStore((state) => state.logout);

  return (
    // UI implementation
  );
}
```

## App Initialization

Update your `App.tsx` to initialize stores:

```typescript
import React, { useEffect, useState } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { initializeStores } from './store';
import { AppNavigator } from './navigation/AppNavigator';

export default function App() {
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    async function prepare() {
      try {
        // Initialize stores and check auth status
        await initializeStores();
      } catch (error) {
        console.error('Failed to initialize app:', error);
      } finally {
        setIsReady(true);
      }
    }

    prepare();
  }, []);

  if (!isReady) {
    return null; // Or loading screen
  }

  return (
    <SafeAreaProvider>
      <NavigationContainer>
        <AppNavigator />
      </NavigationContainer>
    </SafeAreaProvider>
  );
}
```

## Environment Configuration

Create `.env` file in project root:

```bash
EXPO_PUBLIC_API_URL=http://localhost:3000/api
```

For production:
```bash
EXPO_PUBLIC_API_URL=https://api.edulens.com/api
```

## Package Dependencies

All required packages have been installed:

```json
{
  "dependencies": {
    "zustand": "^4.x",
    "axios": "^1.x",
    "@react-native-async-storage/async-storage": "^1.x",
    "expo-secure-store": "~13.0.0",
    "react-native-ble-plx": "^3.1.0"
  }
}
```

## Key Features

### State Management
- ✅ Zustand for lightweight, performant state
- ✅ Automatic persistence (SecureStore + AsyncStorage)
- ✅ Type-safe with full TypeScript support
- ✅ Selector-based optimization
- ✅ DevTools integration

### API Communication
- ✅ Centralized HTTP client
- ✅ Automatic token refresh
- ✅ Request/response interceptors
- ✅ Standardized error handling
- ✅ Type-safe responses

### Bluetooth
- ✅ Device scanning and filtering
- ✅ Connection management
- ✅ Command/response protocol
- ✅ Real-time notifications
- ✅ Auto-reconnection

### Developer Experience
- ✅ Custom hooks for easy access
- ✅ Comprehensive type definitions
- ✅ Clean separation of concerns
- ✅ Consistent error handling
- ✅ Dev tools for debugging

## Testing

Test the setup:

```typescript
// In any component
import { useAuth, useDevice, useChild } from '../hooks';

function TestComponent() {
  const auth = useAuth();
  const device = useDevice();
  const child = useChild();

  console.log('Auth state:', auth);
  console.log('Device state:', device);
  console.log('Child state:', child);
}
```

Access stores from console (dev mode):

```javascript
// In browser console or React Native debugger
__EDULENS_STORES__.getAuthState()
__EDULENS_STORES__.getDeviceState()
__EDULENS_STORES__.getChildState()
```

## Next Steps

1. **Update Navigation**
   - Add auth guards using `useAuth().isAuthenticated`
   - Implement protected routes

2. **Migrate Context Components**
   - Replace `AuthContext` with `useAuth` hook
   - Replace `BluetoothContext` with `useDevice` hook

3. **Implement Screens**
   - Use hooks to access state and actions
   - Display loading and error states

4. **Add API Integration**
   - Configure backend URL
   - Test authentication flow
   - Implement data fetching

5. **Test Bluetooth**
   - Request permissions
   - Test device scanning
   - Verify connection flow

## Common Patterns

### Loading State

```typescript
function MyScreen() {
  const { isLoading, data, error } = useChild();

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;

  return <DataDisplay data={data} />;
}
```

### Error Handling

```typescript
function MyScreen() {
  const { addChild, error, clearError } = useChild();

  const handleSubmit = async (data) => {
    clearError(); // Clear previous errors
    const success = await addChild(data);

    if (!success) {
      // Show error message
      Alert.alert('Error', error || 'Failed to add child');
    }
  };
}
```

### Optimistic Updates

```typescript
function MyScreen() {
  const { updateChild } = useChild();
  const [localState, setLocalState] = useState(data);

  const handleUpdate = async (updates) => {
    // Update UI immediately
    setLocalState({ ...localState, ...updates });

    // Sync with backend
    const success = await updateChild(id, updates);

    if (!success) {
      // Revert on failure
      setLocalState(data);
    }
  };
}
```

## Troubleshooting

### Store not persisting
- Check AsyncStorage/SecureStore permissions
- Verify `partialize` configuration in store

### Type errors
- Run `npm run typecheck`
- Ensure types are imported from `../types`

### Bluetooth not working
- Check permissions in `app.json`
- Verify BLE enabled on device
- Check service UUIDs match hardware

### API calls failing
- Verify `EXPO_PUBLIC_API_URL` is set
- Check network connectivity
- Verify backend is running

## Documentation

- **Architecture Guide**: `/docs/ARCHITECTURE.md` - Detailed architecture documentation
- **API Reference**: (To be created) - API endpoint documentation
- **Component Library**: (To be created) - UI component documentation

## Support

For questions or issues:
1. Check documentation in `/docs`
2. Review example usage in hooks
3. Check type definitions for API contracts
4. Use dev tools for debugging

---

**Ready to build!** The architecture is complete and ready for feature development.
