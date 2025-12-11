/**
 * API Service for EduLens Parent Companion App
 * Centralized HTTP client with authentication, error handling, and interceptors
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosError } from 'axios';
import type { ApiResponse, ApiError } from '../types';

// ============================================================================
// Configuration
// ============================================================================

const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:3000/api';
const API_TIMEOUT = 30000; // 30 seconds

// ============================================================================
// API Client Class
// ============================================================================

class ApiService {
  private client: AxiosInstance;
  private refreshTokenPromise: Promise<string> | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: API_TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
    });

    this.setupInterceptors();
  }

  // ==========================================================================
  // Interceptor Setup
  // ==========================================================================

  private setupInterceptors(): void {
    // Request interceptor - Add auth token to requests
    this.client.interceptors.request.use(
      async (config) => {
        const token = await this.getAccessToken();

        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }

        // Add request ID for tracking
        config.headers['X-Request-ID'] = this.generateRequestId();

        // Add platform info
        config.headers['X-Platform'] = 'react-native';

        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor - Handle errors and token refresh
    this.client.interceptors.response.use(
      (response) => {
        // Transform successful responses to standardized format
        return response;
      },
      async (error: AxiosError) => {
        const originalRequest = error.config as AxiosRequestConfig & {
          _retry?: boolean;
        };

        // Handle 401 Unauthorized - Token expired
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            // Attempt to refresh token
            const newToken = await this.handleTokenRefresh();

            if (newToken && originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
              return this.client(originalRequest);
            }
          } catch (refreshError) {
            // Token refresh failed - logout user
            await this.handleAuthFailure();
            return Promise.reject(refreshError);
          }
        }

        // Handle other errors
        return Promise.reject(this.handleError(error));
      }
    );
  }

  // ==========================================================================
  // Token Management
  // ==========================================================================

  private async getAccessToken(): Promise<string | null> {
    try {
      // Dynamically import to avoid circular dependencies
      const { useAuthStore } = await import('../store/slices/authSlice');
      const tokens = useAuthStore.getState().tokens;

      // Check if token is expired or about to expire
      if (tokens && useAuthStore.getState().isTokenExpired()) {
        // Trigger refresh if token is expired
        await this.handleTokenRefresh();
        return useAuthStore.getState().tokens?.accessToken || null;
      }

      return tokens?.accessToken || null;
    } catch (error) {
      console.error('Error getting access token:', error);
      return null;
    }
  }

  private async handleTokenRefresh(): Promise<string> {
    // Prevent multiple simultaneous refresh requests
    if (this.refreshTokenPromise) {
      return this.refreshTokenPromise;
    }

    this.refreshTokenPromise = (async () => {
      try {
        const { useAuthStore } = await import('../store/slices/authSlice');
        await useAuthStore.getState().refreshToken();

        const newToken = useAuthStore.getState().tokens?.accessToken;

        if (!newToken) {
          throw new Error('Token refresh failed');
        }

        return newToken;
      } finally {
        this.refreshTokenPromise = null;
      }
    })();

    return this.refreshTokenPromise;
  }

  private async handleAuthFailure(): Promise<void> {
    try {
      const { useAuthStore } = await import('../store/slices/authSlice');
      await useAuthStore.getState().logout();
    } catch (error) {
      console.error('Error handling auth failure:', error);
    }
  }

  // ==========================================================================
  // Error Handling
  // ==========================================================================

  private handleError(error: AxiosError): ApiError {
    if (error.response) {
      // Server responded with error status
      const data = error.response.data as any;

      return {
        code: data?.code || `HTTP_${error.response.status}`,
        message: data?.message || error.message || 'Request failed',
        details: data?.details,
        validationErrors: data?.validationErrors,
      };
    } else if (error.request) {
      // Request made but no response received
      return {
        code: 'NETWORK_ERROR',
        message: 'Network error. Please check your connection.',
      };
    } else {
      // Error in request configuration
      return {
        code: 'REQUEST_ERROR',
        message: error.message || 'Request configuration error',
      };
    }
  }

  // ==========================================================================
  // Utility Methods
  // ==========================================================================

  private generateRequestId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  // ==========================================================================
  // HTTP Methods
  // ==========================================================================

  async get<T = unknown>(
    url: string,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    try {
      const response = await this.client.get<ApiResponse<T>>(url, config);
      return response.data;
    } catch (error) {
      return {
        success: false,
        error: this.handleError(error as AxiosError),
      };
    }
  }

  async post<T = unknown>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    try {
      const response = await this.client.post<ApiResponse<T>>(url, data, config);
      return response.data;
    } catch (error) {
      return {
        success: false,
        error: this.handleError(error as AxiosError),
      };
    }
  }

  async put<T = unknown>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    try {
      const response = await this.client.put<ApiResponse<T>>(url, data, config);
      return response.data;
    } catch (error) {
      return {
        success: false,
        error: this.handleError(error as AxiosError),
      };
    }
  }

  async patch<T = unknown>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    try {
      const response = await this.client.patch<ApiResponse<T>>(url, data, config);
      return response.data;
    } catch (error) {
      return {
        success: false,
        error: this.handleError(error as AxiosError),
      };
    }
  }

  async delete<T = unknown>(
    url: string,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    try {
      const response = await this.client.delete<ApiResponse<T>>(url, config);
      return response.data;
    } catch (error) {
      return {
        success: false,
        error: this.handleError(error as AxiosError),
      };
    }
  }

  // ==========================================================================
  // File Upload
  // ==========================================================================

  async uploadFile<T = unknown>(
    url: string,
    file: File | Blob,
    fieldName: string = 'file',
    additionalData?: Record<string, any>
  ): Promise<ApiResponse<T>> {
    try {
      const formData = new FormData();
      formData.append(fieldName, file);

      if (additionalData) {
        Object.entries(additionalData).forEach(([key, value]) => {
          formData.append(key, value);
        });
      }

      const response = await this.client.post<ApiResponse<T>>(url, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      return response.data;
    } catch (error) {
      return {
        success: false,
        error: this.handleError(error as AxiosError),
      };
    }
  }

  // ==========================================================================
  // Health Check
  // ==========================================================================

  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.client.get('/health');
      return response.status === 200;
    } catch (error) {
      console.error('Health check failed:', error);
      return false;
    }
  }

  // ==========================================================================
  // Configuration Methods
  // ==========================================================================

  setBaseURL(baseURL: string): void {
    this.client.defaults.baseURL = baseURL;
  }

  setTimeout(timeout: number): void {
    this.client.defaults.timeout = timeout;
  }

  setHeader(key: string, value: string): void {
    this.client.defaults.headers.common[key] = value;
  }

  removeHeader(key: string): void {
    delete this.client.defaults.headers.common[key];
  }
}

// ============================================================================
// Singleton Export
// ============================================================================

export const apiService = new ApiService();

// ============================================================================
// Children API
// ============================================================================

export interface ChildProfile {
  id: string;
  name: string;
  age: number;
  grade: string;
  language: string;
  created_at: string;
  updated_at: string;
}

export interface ChildCreate {
  name: string;
  age: number;
  grade: string;
  language?: string;
  parent_id?: string;
}

export interface ChildUpdate {
  name?: string;
  age?: number;
  grade?: string;
  language?: string;
}

export const childrenApi = {
  create: (data: ChildCreate) =>
    apiService.post<ChildProfile>('/v1/children', data),

  list: (parentId?: string) =>
    apiService.get<ChildProfile[]>(
      parentId ? `/v1/children?parent_id=${parentId}` : '/v1/children'
    ),

  get: (childId: string) =>
    apiService.get<ChildProfile>(`/v1/children/${childId}`),

  update: (childId: string, data: ChildUpdate) =>
    apiService.put<ChildProfile>(`/v1/children/${childId}`, data),

  delete: (childId: string) =>
    apiService.delete(`/v1/children/${childId}`),
};

// ============================================================================
// Voice API
// ============================================================================

export interface VoiceQueryRequest {
  transcript: string;
  child_id?: string;
  session_id?: string;
  language?: string;
}

export interface VoiceQueryResponse {
  response: string;
  response_type: string;
  session_id: string;
  audio_url?: string;
}

export interface TranscriptionResponse {
  transcript: string;
  confidence: number;
  language: string;
}

export const voiceApi = {
  transcribe: (audioFile: Blob, language: string = 'en') => {
    const formData = new FormData();
    formData.append('audio', audioFile);
    formData.append('language', language);
    return apiService.post<TranscriptionResponse>('/v1/voice/transcribe', formData);
  },

  query: (data: VoiceQueryRequest) =>
    apiService.post<VoiceQueryResponse>('/v1/voice/query', data),

  getSynthesizeUrl: (text: string, sessionId?: string) =>
    `${API_BASE_URL}/v1/voice/synthesize?text=${encodeURIComponent(text)}${
      sessionId ? `&session_id=${sessionId}` : ''
    }`,
};

// ============================================================================
// Tutor API (text-based)
// ============================================================================

export interface TutorQueryRequest {
  query: string;
  session_id?: string;
  student_age?: number;
  student_grade?: string;
  subject?: string;
}

export interface TutorResponse {
  response: string;
  response_type: string;
  session_id: string;
  hints_remaining?: number;
  subject_detected?: string;
}

export const tutorApi = {
  query: (data: TutorQueryRequest) =>
    apiService.post<TutorResponse>('/v1/tutor/query', data),

  getSession: (sessionId: string) =>
    apiService.get(`/v1/session/${sessionId}`),

  deleteSession: (sessionId: string) =>
    apiService.delete(`/v1/session/${sessionId}`),

  getSubjects: () =>
    apiService.get('/v1/subjects'),
};

// ============================================================================
// Convenience Exports
// ============================================================================

export default apiService;

// Export types
export type { ApiResponse, ApiError };
