/**
 * TypeScript Type Definitions for EduLens Parent Companion App
 * Comprehensive type definitions for state management, API responses, and domain models
 */

// ============================================================================
// User & Authentication Types
// ============================================================================

export interface User {
  id: string;
  email: string;
  name: string;
  phoneNumber?: string;
  createdAt: string;
  updatedAt: string;
  preferences: UserPreferences;
  subscription?: Subscription;
}

export interface UserPreferences {
  language: string;
  timezone: string;
  notificationsEnabled: boolean;
  emailNotifications: boolean;
  pushNotifications: boolean;
  weeklyReports: boolean;
  theme: 'light' | 'dark' | 'auto';
}

export interface Subscription {
  plan: 'free' | 'basic' | 'premium' | 'family';
  status: 'active' | 'expired' | 'cancelled' | 'trial';
  startDate: string;
  endDate: string;
  autoRenew: boolean;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  expiresAt: string;
  tokenType: 'Bearer';
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  name: string;
  phoneNumber?: string;
  acceptedTerms: boolean;
  parentalConsent: boolean;
}

// ============================================================================
// Child Profile Types
// ============================================================================

export interface ChildProfile {
  id: string;
  parentId: string;
  name: string;
  age: number;
  dateOfBirth: string;
  grade: string;
  school?: string;
  deviceId?: string;
  avatar?: string;
  learningGoals: LearningGoal[];
  preferences: ChildPreferences;
  createdAt: string;
  updatedAt: string;
}

export interface ChildPreferences {
  tutorVoice: 'male' | 'female' | 'neutral';
  tutorSpeed: number; // 0.5 to 2.0
  difficultyLevel: 'beginner' | 'intermediate' | 'advanced' | 'adaptive';
  subjects: string[];
  dailyLearningTimeLimit: number; // minutes
  screenTimeBreakInterval: number; // minutes
  restrictedApps: string[];
}

export interface LearningGoal {
  id: string;
  childId: string;
  title: string;
  description: string;
  category: 'reading' | 'math' | 'science' | 'language' | 'other';
  targetDate?: string;
  progress: number; // 0-100
  status: 'active' | 'completed' | 'paused';
  createdAt: string;
}

// ============================================================================
// Device Types
// ============================================================================

export interface EduLensDevice {
  id: string;
  name: string;
  serialNumber: string;
  modelNumber: string;
  hardwareVersion: string;
  firmwareVersion: string;
  childId?: string;
  isConnected: boolean;
  isPaired: boolean;
  batteryLevel?: number;
  isCharging?: boolean;
  lastSeen: string;
  connectionType: 'bluetooth' | 'wifi' | 'offline';
  settings: DeviceSettings;
  status: DeviceStatus;
}

export interface DeviceSettings {
  volume: number; // 0-100
  brightness: number; // 0-100
  wakeSensitivity: 'low' | 'medium' | 'high';
  autoShutoffTime: number; // minutes
  privacyMode: boolean;
  locationTracking: boolean;
  microphoneEnabled: boolean;
  cameraEnabled: boolean;
  ocrEnabled: boolean;
  tutoringEnabled: boolean;
  translationEnabled: boolean;
  wifiAutoConnect: boolean;
}

export interface DeviceStatus {
  batteryLevel: number;
  isCharging: boolean;
  temperature: number; // Celsius
  storageUsed: number; // MB
  storageTotal: number; // MB
  activeFeatures: string[];
  wifiConnected: boolean;
  wifiSSID?: string;
  bluetoothConnected: boolean;
  uptime: number; // seconds
  lastSync: string;
  errors: DeviceError[];
}

export interface DeviceError {
  code: string;
  message: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  timestamp: string;
  resolved: boolean;
}

export interface DeviceCommand {
  type: 'SET_VOLUME' | 'SET_BRIGHTNESS' | 'SET_SENSITIVITY' | 'ENABLE_FEATURE' | 'DISABLE_FEATURE' |
        'RESTART' | 'UPDATE_FIRMWARE' | 'SYNC_DATA' | 'CLEAR_CACHE' | 'FACTORY_RESET';
  payload?: Record<string, unknown>;
}

// ============================================================================
// Learning Analytics Types
// ============================================================================

export interface LearningSession {
  id: string;
  childId: string;
  deviceId: string;
  startTime: string;
  endTime?: string;
  duration: number; // seconds
  activities: LearningActivity[];
  summary: SessionSummary;
}

export interface LearningActivity {
  id: string;
  sessionId: string;
  type: 'reading' | 'tutoring' | 'translation' | 'ocr' | 'exploration';
  subject?: string;
  topic?: string;
  startTime: string;
  duration: number; // seconds
  questionsAsked: number;
  answersProvided: number;
  confidence: number; // 0-100
  engagement: number; // 0-100
  metadata: Record<string, unknown>;
}

export interface SessionSummary {
  totalDuration: number;
  questionsAsked: number;
  topicsExplored: string[];
  averageEngagement: number;
  averageConfidence: number;
  wordsRead: number;
  problemsSolved: number;
  skillsImproved: string[];
}

export interface LearningProgress {
  childId: string;
  period: 'daily' | 'weekly' | 'monthly' | 'all-time';
  startDate: string;
  endDate: string;
  totalSessions: number;
  totalDuration: number; // seconds
  averageSessionLength: number; // seconds
  questionsAsked: number;
  topicsExplored: string[];
  subjectBreakdown: SubjectProgress[];
  engagementTrend: DataPoint[];
  confidenceTrend: DataPoint[];
  achievements: Achievement[];
}

export interface SubjectProgress {
  subject: string;
  duration: number; // seconds
  questionsAsked: number;
  confidenceLevel: number; // 0-100
  improvement: number; // percentage change
}

export interface DataPoint {
  date: string;
  value: number;
}

export interface Achievement {
  id: string;
  childId: string;
  title: string;
  description: string;
  category: string;
  icon: string;
  earnedAt: string;
  rarity: 'common' | 'rare' | 'epic' | 'legendary';
}

// ============================================================================
// Notification Types
// ============================================================================

export interface Notification {
  id: string;
  userId: string;
  type: 'info' | 'warning' | 'success' | 'error' | 'achievement';
  title: string;
  message: string;
  data?: Record<string, unknown>;
  read: boolean;
  createdAt: string;
  expiresAt?: string;
  actionUrl?: string;
  actionLabel?: string;
}

// ============================================================================
// API Response Types
// ============================================================================

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: ApiError;
  meta?: ResponseMeta;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  validationErrors?: ValidationError[];
}

export interface ValidationError {
  field: string;
  message: string;
  code: string;
}

export interface ResponseMeta {
  timestamp: string;
  requestId: string;
  pagination?: PaginationMeta;
}

export interface PaginationMeta {
  page: number;
  pageSize: number;
  totalPages: number;
  totalItems: number;
  hasNextPage: boolean;
  hasPreviousPage: boolean;
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  meta: ResponseMeta & {
    pagination: PaginationMeta;
  };
}

// ============================================================================
// Bluetooth Types
// ============================================================================

export interface BluetoothScanResult {
  id: string;
  name: string;
  rssi: number; // Signal strength
  serviceUUIDs: string[];
  manufacturerData?: string;
  isConnectable: boolean;
}

export interface BluetoothConnectionState {
  deviceId: string;
  state: 'connecting' | 'connected' | 'disconnecting' | 'disconnected';
  error?: string;
}

// ============================================================================
// Store State Types
// ============================================================================

export interface AuthState {
  user: User | null;
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface DeviceState {
  devices: EduLensDevice[];
  connectedDevice: EduLensDevice | null;
  discoveredDevices: BluetoothScanResult[];
  isScanning: boolean;
  isBluetoothEnabled: boolean;
  error: string | null;
}

export interface ChildState {
  children: ChildProfile[];
  activeChild: ChildProfile | null;
  learningProgress: Record<string, LearningProgress>; // childId -> progress
  recentSessions: LearningSession[];
  isLoading: boolean;
  error: string | null;
}

export interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
}

export interface AppState {
  isOnline: boolean;
  lastSyncTime: string | null;
  appVersion: string;
  isUpdateAvailable: boolean;
}

// ============================================================================
// Utility Types
// ============================================================================

export type AsyncStatus = 'idle' | 'loading' | 'success' | 'error';

export interface AsyncState<T = unknown> {
  data: T | null;
  status: AsyncStatus;
  error: string | null;
}

export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};
