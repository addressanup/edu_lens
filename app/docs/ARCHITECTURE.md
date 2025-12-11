# EduLens Companion App - Architecture Documentation

## Overview

The EduLens Parent Companion App is built with React Native and Expo, using modern architecture patterns for scalability, maintainability, and type safety.

## Technology Stack

- **React Native 0.73** - Cross-platform mobile framework
- **Expo ~50.0** - Development and build toolchain
- **TypeScript 5.3** - Type safety and better developer experience
- **Zustand** - Lightweight state management with persistence
- **Axios** - HTTP client for API communication
- **React Native BLE PLX** - Bluetooth Low Energy communication
- **React Navigation** - Navigation library

## Architecture Overview

```
app/src/
├── store/              # State management (Zustand)
│   ├── slices/         # Feature-specific state slices
│   │   ├── authSlice.ts      # Authentication state
│   │   ├── deviceSlice.ts    # Device management state
│   │   └── childSlice.ts     # Child profiles state
│   └── index.ts        # Store exports and utilities
├── services/           # Business logic and external services
│   ├── api.ts          # HTTP client with interceptors
│   └── bluetooth.ts    # Bluetooth Low Energy service
├── hooks/              # Custom React hooks
│   ├── useAuth.ts      # Authentication hook
│   ├── useDevice.ts    # Device management hook
│   └── useChild.ts     # Child profiles hook
├── types/              # TypeScript type definitions
│   └── index.ts        # Centralized type exports
├── screens/            # Screen components
├── components/         # Reusable UI components
├── navigation/         # Navigation configuration
├── theme/              # Styling and theming
├── auth/               # Legacy auth context (to be migrated)
└── bluetooth/          # Legacy BLE context (to be migrated)
```

## State Management

### Why Zustand?

We chose Zustand over Redux for several reasons:

1. **Minimal Boilerplate** - Less code, faster development
2. **Built-in Persistence** - Easy integration with SecureStore and AsyncStorage
3. **TypeScript-First** - Excellent TypeScript support
4. **Performance** - Selector-based optimization built-in
5. **DevTools Support** - React DevTools compatible
6. **Small Bundle Size** - ~1KB vs Redux's ~10KB

### Store Architecture

#### 1. Auth Slice (`authSlice.ts`)

**Purpose**: Manages user authentication, tokens, and session

**State**:
```typescript
{
  user: User | null
  tokens: AuthTokens | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
}
```

**Key Actions**:
- `login(credentials)` - Authenticate user
- `logout()` - Clear session
- `register(data)` - Create new account
- `refreshToken()` - Refresh expired access token
- `updateUser(updates)` - Update profile
- `checkAuthStatus()` - Restore session on app start

**Persistence**:
- Uses Expo SecureStore for sensitive data (tokens)
- Automatically restores session on app restart

#### 2. Device Slice (`deviceSlice.ts`)

**Purpose**: Manages EduLens device connections, settings, and status

**State**:
```typescript
{
  devices: EduLensDevice[]
  connectedDevice: EduLensDevice | null
  discoveredDevices: BluetoothScanResult[]
  isScanning: boolean
  isBluetoothEnabled: boolean
  error: string | null
}
```

**Key Actions**:
- `startScan()` - Scan for nearby devices
- `connectDevice(id)` - Connect via Bluetooth
- `pairDevice(deviceId, childId)` - Pair device to child
- `sendCommand(id, command)` - Send control commands
- `updateDeviceSettings(id, settings)` - Update configuration
- `checkFirmwareUpdate(id)` - Check for updates

**Persistence**:
- Uses AsyncStorage for device list
- Does not persist scanning/connection state

#### 3. Child Slice (`childSlice.ts`)

**Purpose**: Manages child profiles, learning data, and goals

**State**:
```typescript
{
  children: ChildProfile[]
  activeChild: ChildProfile | null
  learningProgress: Record<string, LearningProgress>
  recentSessions: LearningSession[]
  isLoading: boolean
  error: string | null
}
```

**Key Actions**:
- `addChild(data)` - Add new child profile
- `updateChild(id, updates)` - Update profile
- `fetchLearningProgress(id, period)` - Get learning analytics
- `addLearningGoal(id, goal)` - Create learning goal
- `pairDeviceToChild(childId, deviceId)` - Link device

**Persistence**:
- Uses AsyncStorage for children and active child
- Does not persist session/progress data (fetched fresh)

## Services Layer

### API Service (`api.ts`)

Centralized HTTP client built on Axios with advanced features:

**Features**:
- Automatic token injection
- Token refresh on 401
- Request/response interceptors
- Standardized error handling
- Request ID tracking
- Type-safe responses

**Usage**:
```typescript
import { apiService } from '../services/api';

const response = await apiService.get<{ users: User[] }>('/users');
if (response.success) {
  console.log(response.data.users);
}
```

**Authentication Flow**:
1. Request made → Interceptor adds Bearer token
2. If 401 received → Attempt token refresh
3. If refresh succeeds → Retry original request
4. If refresh fails → Logout user

### Bluetooth Service (`bluetooth.ts`)

Manages Bluetooth Low Energy communication with EduLens glasses:

**Features**:
- Device scanning with filtering
- Connection management
- Characteristic read/write
- Notification subscriptions
- Auto-reconnection
- Device status monitoring

**EduLens BLE Protocol**:
- Service UUID: `edu10001-0000-1000-8000-00805f9b34fb`
- Command Characteristic: `edu10002-...`
- Status Characteristic: `edu10003-...`
- Notification Characteristic: `edu10004-...`
- Battery Characteristic: `edu10005-...`

**Usage**:
```typescript
import { bluetoothService } from '../services/bluetooth';

// Scan for devices
await bluetoothService.startScan();

// Connect
await bluetoothService.connect(deviceId);

// Send command
await bluetoothService.sendCommand(deviceId, {
  type: 'SET_VOLUME',
  payload: { volume: 80 }
});
```

## Custom Hooks

### useAuth Hook

Convenience wrapper around auth store with error handling:

```typescript
const {
  user,
  isAuthenticated,
  login,
  logout,
  hasPermission,
  isSubscriptionActive
} = useAuth();
```

**Benefits**:
- Simplified API
- Built-in error handling
- Utility functions
- Type-safe

### useDevice Hook

Complete device management interface:

```typescript
const {
  devices,
  connectedDevice,
  connect,
  sendCommand,
  setVolume,
  getBatteryLevel,
  needsBatteryCharge
} = useDevice();
```

**Features**:
- Device CRUD operations
- Connection management
- Quick action helpers
- Status utilities

### useChild Hook

Child profile and learning data management:

```typescript
const {
  children,
  activeChild,
  learningProgress,
  addChild,
  updateChild,
  fetchProgress,
  getTotalLearningTime
} = useChild(childId);
```

**Features**:
- Profile management
- Learning analytics
- Goal tracking
- Device pairing

## Type System

All types are defined in `/src/types/index.ts`:

**Key Type Categories**:

1. **User & Auth Types** - Authentication and user profiles
2. **Child Profile Types** - Child data and preferences
3. **Device Types** - EduLens hardware and settings
4. **Learning Analytics** - Progress tracking and sessions
5. **API Types** - Request/response structures
6. **Bluetooth Types** - BLE communication

**Type Safety Benefits**:
- Compile-time error checking
- IntelliSense autocomplete
- Self-documenting code
- Refactoring safety

## Data Flow

### Authentication Flow

```
User enters credentials
    ↓
useAuth.login()
    ↓
authStore.login()
    ↓
apiService.post('/auth/login')
    ↓
Store tokens in SecureStore
    ↓
Update store state
    ↓
UI re-renders
```

### Device Connection Flow

```
User taps "Connect"
    ↓
useDevice.connect()
    ↓
deviceStore.connectDevice()
    ↓
bluetoothService.connect()
    ↓
Discover services/characteristics
    ↓
Setup notifications
    ↓
Fetch device details from API
    ↓
Update store state
    ↓
UI shows connected
```

### Data Sync Flow

```
App startup
    ↓
initializeStores()
    ↓
Check auth status
    ↓
If authenticated:
  - Fetch user data
  - Fetch children
  - Fetch devices
  - Enable Bluetooth
    ↓
Periodic syncStoreData()
```

## Security Considerations

### Token Management
- Access tokens stored in Expo SecureStore (encrypted)
- Auto-refresh before expiration
- Secure cleanup on logout

### Data Persistence
- Sensitive data (tokens) → SecureStore
- Non-sensitive data → AsyncStorage
- No plaintext passwords stored

### API Communication
- HTTPS only
- Bearer token authentication
- Request ID tracking
- Error sanitization

### Bluetooth Security
- UUID-based device filtering
- Connection encryption via BLE
- Command validation
- Pairing verification

## Performance Optimization

### State Management
- Selector-based re-renders (only affected components update)
- Persisted state reduces initial load time
- Lazy imports prevent circular dependencies

### API Calls
- Request deduplication (token refresh)
- Response caching (planned)
- Optimistic updates (planned)

### Bluetooth
- Auto-stop scanning after 30s
- Single notification subscription per device
- Cleanup on disconnect

## Migration Path

### From Context to Zustand

The app currently has legacy Context-based state in:
- `/src/auth/AuthContext.tsx`
- `/src/bluetooth/BluetoothContext.tsx`

**Migration Steps**:
1. Update screen components to use new hooks
2. Remove Context providers from App.tsx
3. Delete legacy context files
4. Update navigation guards

**Example Migration**:

Before (Context):
```typescript
import { useAuth } from '../auth/AuthContext';

const { user, login } = useAuth();
```

After (Zustand):
```typescript
import { useAuth } from '../hooks/useAuth';

const { user, login } = useAuth();
```

The API is identical, making migration seamless!

## Development Workflow

### Starting Development

```bash
# Install dependencies
npm install

# Start Expo dev server
npm start

# Run on iOS
npm run ios

# Run on Android
npm run android
```

### Type Checking

```bash
npm run typecheck
```

### Linting

```bash
npm run lint
```

### Testing (Planned)

```bash
npm test
```

## Best Practices

### State Management
1. Use selectors for performance
2. Keep actions async for side effects
3. Handle errors in actions
4. Use hooks for components

### API Calls
1. Always check response.success
2. Handle errors gracefully
3. Show loading states
4. Provide user feedback

### Bluetooth
1. Check connection before commands
2. Handle disconnections gracefully
3. Cleanup subscriptions
4. Request permissions early

### TypeScript
1. Define types before implementation
2. Use strict mode
3. Avoid 'any' types
4. Export from centralized location

## Troubleshooting

### Common Issues

**Token Expired**:
- Automatic refresh should handle this
- If persistent, clear SecureStore and re-login

**Bluetooth Connection Failed**:
- Check permissions
- Verify Bluetooth enabled
- Ensure device in range
- Check device not paired elsewhere

**State Not Persisting**:
- Check AsyncStorage/SecureStore permissions
- Verify partialize config in store
- Clear app data and restart

**Type Errors**:
- Run `npm run typecheck`
- Check import paths
- Verify type definitions match API

## Future Enhancements

1. **Offline Support** - Queue API calls when offline
2. **Real-time Updates** - WebSocket for live data
3. **Push Notifications** - Device alerts and achievements
4. **Analytics** - Usage tracking and insights
5. **Testing** - Unit and integration tests
6. **Accessibility** - Screen reader support
7. **Localization** - Multi-language support

## Contributing

When adding new features:

1. **Define Types First** - Add to `/src/types/index.ts`
2. **Create Store Slice** - If new domain (auth, device, child)
3. **Implement Service** - Business logic in `/src/services`
4. **Create Hook** - Convenience wrapper in `/src/hooks`
5. **Update Documentation** - Keep this file current

## Resources

- [Zustand Documentation](https://github.com/pmndrs/zustand)
- [React Navigation](https://reactnavigation.org/)
- [Expo Documentation](https://docs.expo.dev/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [React Native BLE PLX](https://github.com/dotintent/react-native-ble-plx)

---

**Last Updated**: December 10, 2024
**Version**: 1.0.0
**Maintainer**: EduLens Development Team
