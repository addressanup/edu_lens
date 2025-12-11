/**
 * useLiveMonitor Hook
 *
 * React hook for managing live parent monitoring of child's
 * homework session through EduLens glasses.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { Alert } from 'react-native';
import {
  realtimeStreamService,
  ConnectionStatus,
  ObservationEvent,
  SessionStats,
} from '../services/realtimeStream';
import { useAuth } from '../auth/AuthContext';
import { api } from '../services/api';

// Types
export interface LiveMonitorState {
  isConnected: boolean;
  connectionStatus: ConnectionStatus;
  currentFrame: string | null;
  events: ObservationEvent[];
  sessionStats: SessionStats | null;
  error: string | null;
  isLoading: boolean;
}

export interface LiveMonitorActions {
  startMonitoring: (sessionId: string, notifyChild?: boolean) => Promise<void>;
  stopMonitoring: () => Promise<void>;
  sendMessage: (text: string) => void;
  sendVoice: (audioBase64: string) => void;
  sendEncouragement: (type: EncouragementType) => void;
  clearError: () => void;
  setQuality: (quality: 'low' | 'medium' | 'high' | 'adaptive') => void;
}

export type EncouragementType = 'great_job' | 'keep_going' | 'proud' | 'almost_there';

// Maximum events to keep in memory
const MAX_EVENTS = 50;

/**
 * Live Monitor Hook
 *
 * Provides state and actions for parent monitoring functionality.
 *
 * @param childId - Optional child ID to auto-find active session
 */
export function useLiveMonitor(childId?: string): LiveMonitorState & LiveMonitorActions {
  // Auth context for token
  const { user, token } = useAuth();

  // State
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [currentFrame, setCurrentFrame] = useState<string | null>(null);
  const [events, setEvents] = useState<ObservationEvent[]>([]);
  const [sessionStats, setSessionStats] = useState<SessionStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Refs
  const currentSessionId = useRef<string | null>(null);
  const mounted = useRef(true);

  // Setup callbacks on mount
  useEffect(() => {
    mounted.current = true;

    // Frame callback
    realtimeStreamService.onFrame((frameData) => {
      if (mounted.current) {
        setCurrentFrame(frameData);
      }
    });

    // Event callback
    realtimeStreamService.onEvent((event) => {
      if (mounted.current) {
        setEvents((prev) => {
          const updated = [event, ...prev];
          return updated.slice(0, MAX_EVENTS);
        });
      }
    });

    // Connection status callback
    realtimeStreamService.onConnectionChange((status) => {
      if (mounted.current) {
        setConnectionStatus(status);
        setIsConnected(status === 'connected');
      }
    });

    // Stats callback
    realtimeStreamService.onStatsUpdate((stats) => {
      if (mounted.current) {
        setSessionStats(stats);
      }
    });

    // Error callback
    realtimeStreamService.onError((err) => {
      if (mounted.current) {
        setError(err.message);
        setIsLoading(false);
      }
    });

    // Cleanup on unmount
    return () => {
      mounted.current = false;
      realtimeStreamService.cleanup();
    };
  }, []);

  /**
   * Find active session for a child
   */
  const findActiveSession = useCallback(async (targetChildId: string): Promise<string | null> => {
    try {
      const response = await api.get('/api/v1/parent/sessions', {
        params: { parent_id: user?.id },
      });

      const sessions = response.data.sessions || [];
      const activeSession = sessions.find(
        (s: { child_id: string; state: string }) =>
          s.child_id === targetChildId && s.state === 'observing'
      );

      return activeSession?.session_id || null;
    } catch (err) {
      console.error('[useLiveMonitor] Failed to find session:', err);
      return null;
    }
  }, [user?.id]);

  /**
   * Start monitoring a session
   */
  const startMonitoring = useCallback(async (
    sessionId: string,
    notifyChild = true
  ): Promise<void> => {
    if (!token) {
      setError('Not authenticated');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await realtimeStreamService.connect(sessionId, token, notifyChild);
      currentSessionId.current = sessionId;

      // Clear old state
      setEvents([]);
      setCurrentFrame(null);
      setSessionStats(null);

    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to connect';
      setError(message);
      Alert.alert('Connection Error', message);
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  /**
   * Stop monitoring
   */
  const stopMonitoring = useCallback(async (): Promise<void> => {
    await realtimeStreamService.disconnect();
    currentSessionId.current = null;
    setCurrentFrame(null);
  }, []);

  /**
   * Send text message to child
   */
  const sendMessage = useCallback((text: string): void => {
    if (!isConnected) {
      setError('Not connected');
      return;
    }

    // Get child's language (default to 'en')
    const language = sessionStats?.childId ? 'en' : 'en'; // TODO: Get from child profile

    realtimeStreamService.sendTextMessage(text, language);

    // Add to events as sent message
    setEvents((prev) => [
      {
        type: 'parent_message_sent',
        payload: { text, sender: 'parent' },
        timestamp: Date.now(),
      },
      ...prev,
    ].slice(0, MAX_EVENTS));
  }, [isConnected, sessionStats?.childId]);

  /**
   * Send voice message to child
   */
  const sendVoice = useCallback((audioBase64: string): void => {
    if (!isConnected) {
      setError('Not connected');
      return;
    }

    realtimeStreamService.sendVoiceMessage(audioBase64);

    // Add to events
    setEvents((prev) => [
      {
        type: 'parent_voice_sent',
        payload: { sender: 'parent' },
        timestamp: Date.now(),
      },
      ...prev,
    ].slice(0, MAX_EVENTS));
  }, [isConnected]);

  /**
   * Send encouragement to child
   */
  const sendEncouragement = useCallback((type: EncouragementType): void => {
    if (!isConnected) {
      setError('Not connected');
      return;
    }

    const messages: Record<EncouragementType, string> = {
      great_job: 'Great job!',
      keep_going: 'Keep going!',
      proud: "I'm proud of you!",
      almost_there: 'Almost there!',
    };

    realtimeStreamService.sendEncouragement(type);

    // Add to events
    setEvents((prev) => [
      {
        type: 'encouragement_sent',
        payload: { type, message: messages[type], sender: 'parent' },
        timestamp: Date.now(),
      },
      ...prev,
    ].slice(0, MAX_EVENTS));
  }, [isConnected]);

  /**
   * Clear error state
   */
  const clearError = useCallback((): void => {
    setError(null);
  }, []);

  /**
   * Set stream quality
   */
  const setQuality = useCallback((quality: 'low' | 'medium' | 'high' | 'adaptive'): void => {
    realtimeStreamService.setQuality(quality);
  }, []);

  // Auto-find session if childId provided
  useEffect(() => {
    if (childId && !isConnected && !isLoading) {
      findActiveSession(childId).then((sessionId) => {
        if (sessionId && mounted.current) {
          // Session found - don't auto-connect, just inform
          console.log('[useLiveMonitor] Active session found:', sessionId);
        }
      });
    }
  }, [childId, isConnected, isLoading, findActiveSession]);

  return {
    // State
    isConnected,
    connectionStatus,
    currentFrame,
    events,
    sessionStats,
    error,
    isLoading,
    // Actions
    startMonitoring,
    stopMonitoring,
    sendMessage,
    sendVoice,
    sendEncouragement,
    clearError,
    setQuality,
  };
}

export default useLiveMonitor;
