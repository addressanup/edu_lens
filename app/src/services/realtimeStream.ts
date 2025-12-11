/**
 * Real-time Stream Service for EduLens Parent Monitoring
 *
 * WebSocket client service for live video streaming and
 * bidirectional communication between parent app and backend.
 */

import { Platform } from 'react-native';

// Types
export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'error';

export interface ObservationEvent {
  type: string;
  payload: Record<string, unknown>;
  timestamp: number;
}

export interface SessionStats {
  sessionId: string;
  childId: string;
  duration: number;
  frameCount: number;
  eventCount: number;
  currentSubject?: string;
  currentProblem?: number;
}

export interface StreamQualitySettings {
  fps: number;
  quality: 'low' | 'medium' | 'high' | 'adaptive';
}

// Configuration
const WS_RECONNECT_DELAY = 3000; // 3 seconds
const WS_MAX_RECONNECT_ATTEMPTS = 5;
const WS_PING_INTERVAL = 30000; // 30 seconds

/**
 * Real-time Stream Service
 *
 * Manages WebSocket connection for live parent monitoring.
 */
class RealtimeStreamService {
  private ws: WebSocket | null = null;
  private sessionId: string | null = null;
  private authToken: string | null = null;
  private reconnectAttempts = 0;
  private pingInterval: ReturnType<typeof setInterval> | null = null;
  private lastPongTime = 0;

  // Connection state
  private _status: ConnectionStatus = 'disconnected';
  private _notifyChild = true;

  // Callbacks
  private onFrameCallback: ((frameData: string) => void) | null = null;
  private onEventCallback: ((event: ObservationEvent) => void) | null = null;
  private onConnectionChangeCallback: ((status: ConnectionStatus) => void) | null = null;
  private onStatsUpdateCallback: ((stats: SessionStats) => void) | null = null;
  private onErrorCallback: ((error: Error) => void) | null = null;

  /**
   * Get current connection status
   */
  get status(): ConnectionStatus {
    return this._status;
  }

  /**
   * Check if connected
   */
  get isConnected(): boolean {
    return this._status === 'connected';
  }

  /**
   * Connect to an observation session
   *
   * @param sessionId - Session to connect to
   * @param authToken - JWT authentication token
   * @param notifyChild - Whether to notify child when parent connects
   */
  async connect(
    sessionId: string,
    authToken: string,
    notifyChild = true
  ): Promise<void> {
    if (this.ws && this._status === 'connected') {
      // Already connected to same session
      if (this.sessionId === sessionId) {
        return;
      }
      // Disconnect from current session first
      await this.disconnect();
    }

    this.sessionId = sessionId;
    this.authToken = authToken;
    this._notifyChild = notifyChild;
    this.reconnectAttempts = 0;

    return this.establishConnection();
  }

  /**
   * Establish WebSocket connection
   */
  private async establishConnection(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.setStatus('connecting');

      // Build WebSocket URL
      const baseUrl = this.getBaseUrl();
      const wsUrl = `${baseUrl}/ws/parent/${this.sessionId}?token=${this.authToken}&notify_child=${this._notifyChild}`;

      try {
        this.ws = new WebSocket(wsUrl);

        // Binary type for frames
        this.ws.binaryType = 'arraybuffer';

        // Connection opened
        this.ws.onopen = () => {
          console.log('[RealtimeStream] Connected to session:', this.sessionId);
          this.setStatus('connected');
          this.reconnectAttempts = 0;
          this.startPingInterval();
          resolve();
        };

        // Message received
        this.ws.onmessage = (event) => {
          this.handleMessage(event);
        };

        // Connection error
        this.ws.onerror = (error) => {
          console.error('[RealtimeStream] WebSocket error:', error);
          this.onErrorCallback?.(new Error('WebSocket connection error'));
        };

        // Connection closed
        this.ws.onclose = (event) => {
          console.log('[RealtimeStream] WebSocket closed:', event.code, event.reason);
          this.stopPingInterval();

          if (event.code === 4003) {
            // Unauthorized
            this.setStatus('error');
            this.onErrorCallback?.(new Error('Unauthorized: Cannot access this session'));
          } else if (event.code === 4004) {
            // Session not found
            this.setStatus('error');
            this.onErrorCallback?.(new Error('Session not found'));
          } else if (this._status !== 'disconnected') {
            // Try to reconnect
            this.attemptReconnect();
          }
        };

        // Timeout for connection
        setTimeout(() => {
          if (this._status === 'connecting') {
            this.ws?.close();
            reject(new Error('Connection timeout'));
          }
        }, 10000);

      } catch (error) {
        this.setStatus('error');
        reject(error);
      }
    });
  }

  /**
   * Handle incoming WebSocket message
   */
  private handleMessage(event: MessageEvent): void {
    if (event.data instanceof ArrayBuffer) {
      // Binary data - JPEG frame
      this.handleFrameData(event.data);
    } else if (typeof event.data === 'string') {
      // JSON message
      try {
        const data = JSON.parse(event.data);
        this.handleJsonMessage(data);
      } catch (e) {
        console.warn('[RealtimeStream] Invalid JSON message:', event.data);
      }
    }
  }

  /**
   * Handle binary frame data
   */
  private handleFrameData(data: ArrayBuffer): void {
    // Convert to base64 for display
    const bytes = new Uint8Array(data);
    const binary = bytes.reduce((acc, byte) => acc + String.fromCharCode(byte), '');
    const base64 = btoa(binary);
    const frameData = `data:image/jpeg;base64,${base64}`;

    this.onFrameCallback?.(frameData);
  }

  /**
   * Handle JSON message
   */
  private handleJsonMessage(data: Record<string, unknown>): void {
    const messageType = data.type as string;

    switch (messageType) {
      case 'connected':
        // Connection confirmed
        console.log('[RealtimeStream] Session confirmed:', data.session_id);
        break;

      case 'pong':
        // Ping response
        this.lastPongTime = Date.now();
        break;

      case 'stats':
        // Session stats update
        const stats = data as unknown as SessionStats;
        this.onStatsUpdateCallback?.(stats);
        break;

      default:
        // Observation event
        const event: ObservationEvent = {
          type: messageType,
          payload: data.payload as Record<string, unknown> || data,
          timestamp: (data.timestamp as number) || Date.now(),
        };
        this.onEventCallback?.(event);
    }
  }

  /**
   * Attempt to reconnect after disconnect
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= WS_MAX_RECONNECT_ATTEMPTS) {
      console.log('[RealtimeStream] Max reconnect attempts reached');
      this.setStatus('error');
      this.onErrorCallback?.(new Error('Failed to reconnect after multiple attempts'));
      return;
    }

    this.reconnectAttempts++;
    this.setStatus('reconnecting');
    console.log(`[RealtimeStream] Reconnecting attempt ${this.reconnectAttempts}...`);

    setTimeout(() => {
      if (this._status === 'reconnecting' && this.sessionId && this.authToken) {
        this.establishConnection().catch((error) => {
          console.error('[RealtimeStream] Reconnect failed:', error);
        });
      }
    }, WS_RECONNECT_DELAY);
  }

  /**
   * Start ping interval to keep connection alive
   */
  private startPingInterval(): void {
    this.stopPingInterval();
    this.lastPongTime = Date.now();

    this.pingInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        // Send ping
        this.ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));

        // Check for stale connection
        if (Date.now() - this.lastPongTime > WS_PING_INTERVAL * 2) {
          console.warn('[RealtimeStream] Connection appears stale, reconnecting...');
          this.ws.close();
        }
      }
    }, WS_PING_INTERVAL);
  }

  /**
   * Stop ping interval
   */
  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  /**
   * Set connection status and notify callback
   */
  private setStatus(status: ConnectionStatus): void {
    this._status = status;
    this.onConnectionChangeCallback?.(status);
  }

  /**
   * Get WebSocket base URL
   */
  private getBaseUrl(): string {
    // Get API base URL and convert to WebSocket URL
    const apiUrl = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';
    return apiUrl.replace(/^http/, 'ws');
  }

  // ==========================================
  // Callback Registration
  // ==========================================

  /**
   * Register callback for frame data
   */
  onFrame(callback: (frameData: string) => void): void {
    this.onFrameCallback = callback;
  }

  /**
   * Register callback for observation events
   */
  onEvent(callback: (event: ObservationEvent) => void): void {
    this.onEventCallback = callback;
  }

  /**
   * Register callback for connection status changes
   */
  onConnectionChange(callback: (status: ConnectionStatus) => void): void {
    this.onConnectionChangeCallback = callback;
  }

  /**
   * Register callback for session stats updates
   */
  onStatsUpdate(callback: (stats: SessionStats) => void): void {
    this.onStatsUpdateCallback = callback;
  }

  /**
   * Register callback for errors
   */
  onError(callback: (error: Error) => void): void {
    this.onErrorCallback = callback;
  }

  // ==========================================
  // Message Sending
  // ==========================================

  /**
   * Send text message to child
   */
  sendTextMessage(text: string, language = 'en'): void {
    if (!this.isConnected || !this.ws) {
      console.warn('[RealtimeStream] Cannot send message: not connected');
      return;
    }

    this.ws.send(JSON.stringify({
      type: 'text_message',
      content: text,
      language,
      timestamp: Date.now(),
    }));
  }

  /**
   * Send voice message to child
   *
   * @param audioBase64 - Base64 encoded audio data
   */
  sendVoiceMessage(audioBase64: string): void {
    if (!this.isConnected || !this.ws) {
      console.warn('[RealtimeStream] Cannot send voice: not connected');
      return;
    }

    this.ws.send(JSON.stringify({
      type: 'voice_message',
      content: audioBase64,
      timestamp: Date.now(),
    }));
  }

  /**
   * Send encouragement to child
   *
   * @param type - Encouragement type (great_job, keep_going, proud, almost_there)
   */
  sendEncouragement(type: string): void {
    if (!this.isConnected || !this.ws) {
      console.warn('[RealtimeStream] Cannot send encouragement: not connected');
      return;
    }

    this.ws.send(JSON.stringify({
      type: 'encouragement',
      content: type,
      timestamp: Date.now(),
    }));
  }

  /**
   * Request quality change
   */
  setQuality(quality: 'low' | 'medium' | 'high' | 'adaptive'): void {
    if (!this.isConnected || !this.ws) {
      return;
    }

    this.ws.send(JSON.stringify({
      type: 'quality',
      quality,
    }));
  }

  /**
   * Report bandwidth measurement for adaptive quality
   */
  reportBandwidth(bandwidthKbps: number): void {
    if (!this.isConnected || !this.ws) {
      return;
    }

    this.ws.send(JSON.stringify({
      type: 'bandwidth',
      bandwidth_kbps: bandwidthKbps,
    }));
  }

  // ==========================================
  // Disconnect
  // ==========================================

  /**
   * Disconnect from session
   */
  async disconnect(): Promise<void> {
    console.log('[RealtimeStream] Disconnecting...');

    this.setStatus('disconnected');
    this.stopPingInterval();

    if (this.ws) {
      try {
        this.ws.close(1000, 'Client disconnect');
      } catch (e) {
        // Ignore close errors
      }
      this.ws = null;
    }

    this.sessionId = null;
    this.authToken = null;
    this.reconnectAttempts = 0;
  }

  /**
   * Clean up all resources
   */
  cleanup(): void {
    this.disconnect();
    this.onFrameCallback = null;
    this.onEventCallback = null;
    this.onConnectionChangeCallback = null;
    this.onStatsUpdateCallback = null;
    this.onErrorCallback = null;
  }
}

// Export singleton instance
export const realtimeStreamService = new RealtimeStreamService();

// Export class for testing
export { RealtimeStreamService };
