/**
 * Live tutoring client: WebSocket connection + camera frame streaming.
 *
 * Protocol (JSON text frames) matches src/api/live_ws.py on the backend.
 */

import { manipulateAsync, SaveFormat } from 'expo-image-manipulator';

export type TutorEvent =
  | { type: 'connected'; payload: { session_id: string; vision_model?: string } }
  | { type: 'observation_started'; payload: { interval_s: number } }
  | { type: 'observation_stopped'; payload: Record<string, never> }
  | { type: 'observation'; payload: ObservationPayload }
  | { type: 'tutor_response'; payload: TutorResponsePayload }
  | { type: 'frames_ack'; payload: { frames_received: number } }
  | { type: 'config_applied'; payload: Record<string, unknown> }
  | { type: 'pong'; payload: { stats: Record<string, unknown> } }
  | { type: 'error'; payload: { message: string } };

export interface ObservationPayload {
  scene?: string | null;
  subject?: string | null;
  child_present?: boolean;
  engagement?: string | null;
  struggle_detected?: boolean;
  confidence?: number;
  intervention?: string | null;
}

export interface TutorResponsePayload {
  question: string;
  text: string;
  model?: string;
  usage?: Record<string, number>;
}

export interface ChatMessage {
  id: string;
  role: 'tutor' | 'child' | 'system';
  text: string;
  timestamp: number;
}

const FRAME_INTERVAL_MS = 1500;

export interface CapturedPhoto {
  uri: string;
  base64?: string;
}

export class LiveTutorClient {
  private ws: WebSocket | null = null;
  private frameTimer: ReturnType<typeof setInterval> | null = null;
  private capturing = false;

  onEvent: (event: TutorEvent) => void = () => {};
  onStatusChange: (status: 'disconnected' | 'connecting' | 'connected') => void = () => {};
  capturePhoto: () => Promise<CapturedPhoto | null>;

  constructor(capturePhoto: () => Promise<CapturedPhoto | null>) {
    this.capturePhoto = capturePhoto;
  }

  connect(serverUrl: string): void {
    if (this.ws) this.disconnect();

    const wsUrl = serverUrl.replace(/^http/, 'ws').replace(/\/$/, '') + '/ws/live/' + this.sessionId();
    this.onStatusChange('connecting');
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      this.ws = ws;
      this.onStatusChange('connected');
    };
    ws.onmessage = (raw) => {
      try {
        const event = JSON.parse(String(raw.data)) as TutorEvent;
        this.onEvent(event);
      } catch {
        // ignore malformed frames
      }
    };
    ws.onerror = () => this.onStatusChange('disconnected');
    ws.onclose = () => {
      this.ws = null;
      this.stopFrameLoop();
      this.onStatusChange('disconnected');
    };
  }

  disconnect(): void {
    this.stopFrameLoop();
    if (this.ws) {
      try {
        this.ws.close();
      } catch {
        // already closed
      }
      this.ws = null;
    }
    this.onStatusChange('disconnected');
  }

  async startObservation(): Promise<void> {
    this.send({ type: 'start_observation' });
    this.startFrameLoop();
  }

  stopObservation(): void {
    this.send({ type: 'stop_observation' });
    this.stopFrameLoop();
  }

  askQuestion(text: string): void {
    this.send({ type: 'query', text });
  }

  sendConfig(config: { child_name?: string; child_age?: number }): void {
    this.send({ type: 'config', config });
  }

  // ------------------------------------------------------------------

  private send(obj: Record<string, unknown>): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(obj));
    }
  }

  private startFrameLoop(): void {
    if (this.frameTimer) return;
    this.frameTimer = setInterval(() => {
      void this.captureAndSend();
    }, FRAME_INTERVAL_MS);
    void this.captureAndSend();
  }

  private stopFrameLoop(): void {
    if (this.frameTimer) {
      clearInterval(this.frameTimer);
      this.frameTimer = null;
    }
  }

  private async captureAndSend(): Promise<void> {
    if (this.capturing || !this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    this.capturing = true;
    try {
      const photo = await this.capturePhoto();
      if (!photo?.uri) return;

      // Downscale for bandwidth: width 768 keeps homework text readable
      const resized = await manipulateAsync(
        photo.uri,
        [{ resize: { width: 768 } }],
        { compress: 0.5, format: SaveFormat.JPEG, base64: true }
      );
      if (resized.base64) {
        this.send({
          type: 'frame',
          data: resized.base64,
          width: resized.width,
          height: resized.height,
        });
      }
    } catch {
      // Frame skipped (camera busy, connection down) - next tick retries
    } finally {
      this.capturing = false;
    }
  }

  private sessionId(): string {
    // Stable per app install is fine for v1
    return 'student-' + Math.random().toString(36).slice(2, 10);
  }
}
