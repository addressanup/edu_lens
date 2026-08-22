/**
 * EduLens Student App
 *
 * Point the phone camera at your homework. The AI tutor watches the live
 * stream, detects when you're stuck, and speaks up with friendly hints.
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Animated,
  Easing,
  KeyboardAvoidingView,
  LayoutAnimation,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  UIManager,
  View,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as Speech from 'expo-speech';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider, useSafeAreaInsets } from 'react-native-safe-area-context';

import { ChatMessage, LiveTutorClient, TutorEvent } from './src/liveClient';

const SERVER_URL_KEY = 'edulens.serverUrl';
const DEFAULT_SERVER = 'http://192.168.1.100:8000';

type Status = 'disconnected' | 'connecting' | 'connected';

if (
  Platform.OS === 'android' &&
  UIManager.setLayoutAnimationEnabledExperimental
) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

let messageId = 0;
function nextId(): string {
  messageId += 1;
  return `m${messageId}`;
}

// ---------------------------------------------------------------------------
// Small components
// ---------------------------------------------------------------------------

function StatusPill({ status }: { status: Status }) {
  const color =
    status === 'connected' ? '#4ADE80' : status === 'connecting' ? '#FBBF24' : '#94A3B8';
  const label = status === 'connected' ? 'Live' : status === 'connecting' ? 'Connecting' : 'Offline';
  return (
    <View style={[styles.pill, { borderColor: `${color}55` }]}>
      <View style={[styles.pillDot, { backgroundColor: color }]} />
      <Text style={[styles.pillText, { color }]}>{label}</Text>
    </View>
  );
}

function LiveBadge() {
  const pulse = useRef(new Animated.Value(0.35)).current;
  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 1, duration: 700, easing: Easing.ease, useNativeDriver: true }),
        Animated.timing(pulse, { toValue: 0.35, duration: 700, easing: Easing.ease, useNativeDriver: true }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [pulse]);
  return (
    <View style={styles.liveBadge}>
      <Animated.View style={[styles.liveDot, { opacity: pulse }]} />
      <Text style={styles.liveText}>LIVE</Text>
    </View>
  );
}

function ThinkingDots() {
  const a = useRef(new Animated.Value(0)).current;
  const b = useRef(new Animated.Value(0)).current;
  const c = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    const make = (v: Animated.Value, delay: number) =>
      Animated.loop(
        Animated.sequence([
          Animated.delay(delay),
          Animated.timing(v, { toValue: -5, duration: 260, easing: Easing.ease, useNativeDriver: true }),
          Animated.timing(v, { toValue: 0, duration: 260, easing: Easing.ease, useNativeDriver: true }),
          Animated.delay(320),
        ])
      );
    const l1 = make(a, 0), l2 = make(b, 140), l3 = make(c, 280);
    l1.start(); l2.start(); l3.start();
    return () => { l1.stop(); l2.stop(); l3.stop(); };
  }, [a, b, c]);
  return (
    <View style={styles.dotsRow}>
      {[a, b, c].map((v, i) => (
        <Animated.View key={i} style={[styles.dot, { transform: [{ translateY: v }] }]} />
      ))}
    </View>
  );
}

function Avatar({ role }: { role: 'tutor' | 'child' }) {
  return (
    <View style={[styles.avatar, { backgroundColor: role === 'tutor' ? '#6366F1' : '#F59E0B' }]}>
      <Text style={styles.avatarText}>{role === 'tutor' ? 'E' : 'Me'}</Text>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Main app
// ---------------------------------------------------------------------------

function App() {
  const cameraRef = useRef<CameraView>(null);
  const clientRef = useRef<LiveTutorClient | null>(null);
  const scrollRef = useRef<ScrollView>(null);
  const [permission, requestPermission] = useCameraPermissions();

  const [cameraReady, setCameraReady] = useState(false);
  const [serverUrl, setServerUrl] = useState(DEFAULT_SERVER);
  const [editingUrl, setEditingUrl] = useState(false);
  const [status, setStatus] = useState<Status>('disconnected');
  const [observing, setObserving] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState('');
  const [thinking, setThinking] = useState(false);
  const insets = useSafeAreaInsets();

  // Bootstrap
  useEffect(() => {
    (async () => {
      if (!permission?.granted) await requestPermission();
      const saved = await AsyncStorage.getItem(SERVER_URL_KEY);
      if (saved) setServerUrl(saved);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const addMessage = useCallback((role: ChatMessage['role'], text: string) => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setMessages((prev) => [...prev.slice(-49), { id: nextId(), role, text, timestamp: Date.now() }]);
  }, []);

  const speak = useCallback((text: string) => {
    Speech.speak(text, { rate: 0.95, pitch: 1.1 });
  }, []);

  const handleEvent = useCallback(
    (event: TutorEvent) => {
      switch (event.type) {
        case 'connected':
          addMessage('system', 'Connected. Start a homework session or ask anything.');
          break;
        case 'observation_started':
          addMessage('system', 'EduLens is watching your homework.');
          break;
        case 'observation_stopped':
          addMessage('system', 'Observation paused.');
          break;
        case 'tutor_response':
          setThinking(false);
          addMessage('tutor', event.payload.text);
          speak(event.payload.text);
          break;
        case 'observation':
          if (event.payload.intervention) {
            addMessage('tutor', event.payload.intervention);
            speak(event.payload.intervention);
          }
          break;
        case 'error':
          setThinking(false);
          addMessage('system', event.payload.message);
          break;
        default:
          break;
      }
    },
    [addMessage, speak]
  );

  const ensureClient = useCallback((): LiveTutorClient => {
    if (!clientRef.current) {
      clientRef.current = new LiveTutorClient(async () => {
        if (!cameraRef.current || !cameraReady) return null;
        try {
          return await cameraRef.current.takePictureAsync({
            quality: 0.4,
            base64: true,
            skipProcessing: true,
          });
        } catch {
          return null;
        }
      });
      clientRef.current.onEvent = handleEvent;
      clientRef.current.onStatusChange = setStatus;
    }
    return clientRef.current;
  }, [cameraReady, handleEvent]);

  const connect = useCallback(async () => {
    const client = ensureClient();
    await AsyncStorage.setItem(SERVER_URL_KEY, serverUrl.trim());
    setEditingUrl(false);
    setMessages([]);
    addMessage('system', `Connecting to ${serverUrl.trim()}...`);
    client.connect(serverUrl.trim());
  }, [addMessage, ensureClient, serverUrl]);

  const toggleObservation = useCallback(() => {
    const client = clientRef.current;
    if (!client || status !== 'connected') return;
    if (observing) {
      client.stopObservation();
      setObserving(false);
    } else {
      setObserving(true);
      void client.startObservation();
    }
  }, [observing, status]);

  const ask = useCallback(() => {
    const text = question.trim();
    if (!text || status !== 'connected') return;
    addMessage('child', text);
    setQuestion('');
    setThinking(true);
    clientRef.current?.askQuestion(text);
  }, [addMessage, question, status]);

  // Auto-scroll chat
  useEffect(() => {
    if (messages.length) {
      requestAnimationFrame(() => scrollRef.current?.scrollToEnd({ animated: true }));
    }
  }, [messages, thinking]);

  // ------------------------------------------------------------------
  // Permission gates
  // ------------------------------------------------------------------

  if (!permission) {
    return (
      <View style={[styles.root, styles.centered, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
        <ActivityIndicator color="#818CF8" size="large" />
        <Text style={styles.gateText}>Getting things ready...</Text>
        <StatusBar style="light" />
      </View>
    );
  }

  if (!permission.granted) {
    return (
      <View style={[styles.root, styles.centered, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
        <View style={styles.gateIcon}>
          <Text style={styles.gateIconText}>E</Text>
        </View>
        <Text style={styles.gateTitle}>Camera access needed</Text>
        <Text style={styles.gateText}>
          EduLens uses the camera to see your homework and help you learn.
        </Text>
        <Pressable style={({ pressed }) => [styles.primaryButton, pressed && { opacity: 0.85 }]} onPress={requestPermission}>
          <Text style={styles.primaryButtonText}>Allow camera</Text>
        </Pressable>
        <StatusBar style="light" />
      </View>
    );
  }

  // ------------------------------------------------------------------
  // Main render
  // ------------------------------------------------------------------

  return (
    <KeyboardAvoidingView
      style={[styles.root, { paddingTop: insets.top, paddingBottom: insets.bottom }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 40 : 0}
    >
      <StatusBar style="light" />

      {/* Header */}
      <View style={styles.header}>
        <View style={styles.brandRow}>
          <View style={styles.logo}>
            <Text style={styles.logoText}>E</Text>
          </View>
          <Text style={styles.title}>EduLens</Text>
        </View>
        <StatusPill status={status} />
      </View>

      {/* Connection card */}
      {status !== 'connected' && (
        <View style={styles.serverCard}>
          <Text style={styles.serverLabel}>TUTOR SERVER</Text>
          <View style={styles.serverRow}>
            <TextInput
              style={[styles.urlInput, !editingUrl && styles.urlInputStatic]}
              value={serverUrl}
              onChangeText={setServerUrl}
              placeholder="http://192.168.x.x:8000"
              placeholderTextColor="#475569"
              editable={editingUrl}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="url"
            />
            <Pressable
              style={({ pressed }) => [styles.chipButton, pressed && { opacity: 0.8 }]}
              onPress={() => setEditingUrl(!editingUrl)}
            >
              <Text style={styles.chipButtonText}>{editingUrl ? 'Done' : 'Edit'}</Text>
            </Pressable>
            <Pressable
              style={({ pressed }) => [styles.chipButton, styles.chipPrimary, pressed && { opacity: 0.8 }]}
              onPress={() => void connect()}
              disabled={status === 'connecting'}
            >
              {status === 'connecting' ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <Text style={styles.chipButtonText}>Connect</Text>
              )}
            </Pressable>
          </View>
        </View>
      )}

      {/* Camera card */}
      <View style={styles.cameraCard}>
        <CameraView
          ref={cameraRef}
          style={styles.camera}
          facing="back"
          onCameraReady={() => setCameraReady(true)}
        />
        {!cameraReady && (
          <View style={styles.cameraOverlay}>
            <ActivityIndicator color="#A5B4FC" />
            <Text style={styles.cameraHint}>Starting camera...</Text>
          </View>
        )}
        {cameraReady && !observing && (
          <View style={styles.cameraOverlay} pointerEvents="none">
            <View style={styles.cameraHintCard}>
              <Text style={styles.cameraHintTitle}>Ready when you are</Text>
              <Text style={styles.cameraHint}>
                Point the camera at your workbook, then start the session.
              </Text>
            </View>
          </View>
        )}
        {observing && <LiveBadge />}
      </View>

      {/* Chat */}
      <View style={styles.chatArea}>
        <ScrollView ref={scrollRef} style={styles.chatScroll} contentContainerStyle={styles.chatContent}>
          {messages.length === 0 && !thinking && (
            <View style={styles.emptyState}>
              <View style={styles.emptyIcon}>
                <Text style={styles.emptyIconText}>?</Text>
              </View>
              <Text style={styles.emptyTitle}>Stuck on a problem?</Text>
              <Text style={styles.emptyText}>
                Connect to your tutor, start a session, then just ask - I can see what you see.
              </Text>
            </View>
          )}
          {messages.map((m) =>
            m.role === 'system' ? (
              <View key={m.id} style={styles.systemChip}>
                <Text style={styles.systemChipText}>{m.text}</Text>
              </View>
            ) : (
              <View
                key={m.id}
                style={[styles.messageRow, m.role === 'child' && styles.messageRowChild]}
              >
                <Avatar role={m.role === 'child' ? 'child' : 'tutor'} />
                <View style={[styles.bubble, m.role === 'child' ? styles.bubbleChild : styles.bubbleTutor]}>
                  <Text style={m.role === 'child' ? styles.bubbleChildText : styles.bubbleTutorText}>
                    {m.text}
                  </Text>
                </View>
              </View>
            )
          )}
          {thinking && (
            <View style={styles.messageRow}>
              <Avatar role="tutor" />
              <View style={[styles.bubble, styles.bubbleTutor]}>
                <ThinkingDots />
              </View>
            </View>
          )}
        </ScrollView>

        {/* Session control */}
        <Pressable
          onPress={toggleObservation}
          disabled={status !== 'connected' || !cameraReady}
          style={({ pressed }) => [
            styles.sessionButton,
            observing ? styles.sessionStop : styles.sessionStart,
            (status !== 'connected' || !cameraReady) && styles.disabled,
            pressed && { opacity: 0.85 },
          ]}
        >
          <View style={[styles.sessionDot, observing && styles.sessionDotActive]} />
          <Text style={styles.sessionButtonText}>
            {observing ? 'Stop session' : 'Start homework session'}
          </Text>
        </Pressable>

        {/* Question input */}
        <View style={styles.inputDock}>
          <TextInput
            style={styles.input}
            value={question}
            onChangeText={setQuestion}
            placeholder="Ask about your homework..."
            placeholderTextColor="#64748B"
            onSubmitEditing={ask}
            returnKeyType="send"
          />
          <Pressable
            onPress={ask}
            disabled={status !== 'connected' || !question.trim()}
            style={({ pressed }) => [
              styles.sendButton,
              (status !== 'connected' || !question.trim()) && styles.disabled,
              pressed && { opacity: 0.85 },
            ]}
          >
            <Text style={styles.sendButtonText}>Ask</Text>
          </Pressable>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const RADIUS = 16;

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#0B1120' },
  centered: { alignItems: 'center', justifyContent: 'center', padding: 32, gap: 12 },

  // Gates
  gateIcon: {
    width: 72, height: 72, borderRadius: 20, backgroundColor: '#4F46E5',
    alignItems: 'center', justifyContent: 'center', marginBottom: 8,
  },
  gateIconText: { color: '#fff', fontSize: 34, fontWeight: '800' },
  gateTitle: { color: '#F1F5F9', fontSize: 22, fontWeight: '700' },
  gateText: { color: '#94A3B8', fontSize: 15, textAlign: 'center', lineHeight: 22 },
  primaryButton: {
    marginTop: 10, backgroundColor: '#4F46E5', paddingHorizontal: 28,
    paddingVertical: 14, borderRadius: 14,
  },
  primaryButtonText: { color: '#fff', fontWeight: '800', fontSize: 16 },

  // Header
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: 20, paddingTop: 14, paddingBottom: 10,
  },
  brandRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  logo: {
    width: 34, height: 34, borderRadius: 10, backgroundColor: '#4F46E5',
    alignItems: 'center', justifyContent: 'center',
  },
  logoText: { color: '#fff', fontSize: 18, fontWeight: '800' },
  title: { color: '#F8FAFC', fontSize: 21, fontWeight: '800', letterSpacing: 0.2 },

  pill: {
    flexDirection: 'row', alignItems: 'center', borderWidth: 1,
    paddingHorizontal: 10, paddingVertical: 5, borderRadius: 999, gap: 6,
  },
  pillDot: { width: 7, height: 7, borderRadius: 4 },
  pillText: { fontSize: 12, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5 },

  // Server card
  serverCard: {
    marginHorizontal: 16, marginBottom: 12, padding: 14,
    backgroundColor: '#111C33', borderRadius: RADIUS, borderWidth: 1, borderColor: '#1E293B',
  },
  serverLabel: {
    color: '#64748B', fontSize: 11, fontWeight: '700', letterSpacing: 1, marginBottom: 8,
  },
  serverRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  urlInput: {
    flex: 1, color: '#E2E8F0', fontSize: 14, backgroundColor: '#0B1120',
    borderRadius: 10, borderWidth: 1, borderColor: '#334155', paddingHorizontal: 12, paddingVertical: 9,
  },
  urlInputStatic: { borderColor: 'transparent', backgroundColor: 'transparent', paddingHorizontal: 0 },
  chipButton: {
    paddingHorizontal: 14, paddingVertical: 10, borderRadius: 10,
    backgroundColor: '#1E293B', minWidth: 64, alignItems: 'center',
  },
  chipPrimary: { backgroundColor: '#4F46E5' },
  chipButtonText: { color: '#fff', fontSize: 13, fontWeight: '700' },

  // Camera
  cameraCard: {
    flex: 1, marginHorizontal: 16, borderRadius: 24, overflow: 'hidden',
    borderWidth: 1, borderColor: '#233047', backgroundColor: '#000',
  },
  camera: { flex: 1 },
  cameraOverlay: {
    position: 'absolute' as const, top: 0, left: 0, right: 0, bottom: 0,
    alignItems: 'center', justifyContent: 'flex-end', padding: 18,
  },
  cameraHintCard: {
    backgroundColor: '#0B1120CC', borderRadius: 14, paddingVertical: 12, paddingHorizontal: 16,
    borderWidth: 1, borderColor: '#233047', alignItems: 'center',
  },
  cameraHintTitle: { color: '#E2E8F0', fontWeight: '700', fontSize: 14, marginBottom: 2 },
  cameraHint: { color: '#94A3B8', fontSize: 13, textAlign: 'center', lineHeight: 18 },
  liveBadge: {
    position: 'absolute', top: 14, left: 14, flexDirection: 'row', alignItems: 'center',
    backgroundColor: '#DC2626E6', paddingHorizontal: 10, paddingVertical: 5, borderRadius: 8, gap: 6,
  },
  liveDot: { width: 7, height: 7, borderRadius: 4, backgroundColor: '#fff' },
  liveText: { color: '#fff', fontSize: 11, fontWeight: '800', letterSpacing: 1 },

  // Chat
  chatArea: { flex: 1.15, paddingTop: 10 },
  chatScroll: { flex: 1 },
  chatContent: { paddingHorizontal: 16, paddingBottom: 8, gap: 2 },
  emptyState: { alignItems: 'center', paddingTop: 28, paddingHorizontal: 24 },
  emptyIcon: {
    width: 52, height: 52, borderRadius: 26, backgroundColor: '#1E293B',
    alignItems: 'center', justifyContent: 'center', marginBottom: 12,
  },
  emptyIconText: { color: '#818CF8', fontSize: 24, fontWeight: '800' },
  emptyTitle: { color: '#E2E8F0', fontSize: 17, fontWeight: '700', marginBottom: 4 },
  emptyText: { color: '#64748B', fontSize: 14, textAlign: 'center', lineHeight: 20 },

  messageRow: { flexDirection: 'row', alignItems: 'flex-end', marginBottom: 8, gap: 8 },
  messageRowChild: { flexDirection: 'row-reverse' },
  avatar: {
    width: 30, height: 30, borderRadius: 15, alignItems: 'center', justifyContent: 'center',
    marginBottom: 2,
  },
  avatarText: { color: '#fff', fontSize: 11, fontWeight: '800' },
  bubble: {
    maxWidth: '78%', borderRadius: 18, paddingHorizontal: 14, paddingVertical: 10,
  },
  bubbleTutor: {
    backgroundColor: '#1E2745', borderBottomLeftRadius: 6, borderWidth: 1, borderColor: '#2A3655',
  },
  bubbleChild: { backgroundColor: '#4F46E5', borderBottomRightRadius: 6 },
  bubbleTutorText: { color: '#EDF1FF', fontSize: 15, lineHeight: 21 },
  bubbleChildText: { color: '#fff', fontSize: 15, lineHeight: 21 },

  systemChip: {
    alignSelf: 'center', backgroundColor: '#16203A', borderRadius: 999,
    paddingHorizontal: 14, paddingVertical: 6, marginVertical: 6,
  },
  systemChipText: { color: '#7C8DB0', fontSize: 12 },

  dotsRow: { flexDirection: 'row', gap: 5, paddingVertical: 4, paddingHorizontal: 2 },
  dot: { width: 7, height: 7, borderRadius: 4, backgroundColor: '#818CF8' },

  // Controls
  sessionButton: {
    marginHorizontal: 16, marginTop: 8, marginBottom: 8, borderRadius: 14,
    paddingVertical: 15, alignItems: 'center', justifyContent: 'center',
    flexDirection: 'row', gap: 8,
  },
  sessionStart: { backgroundColor: '#4F46E5' },
  sessionStop: { backgroundColor: '#B91C1C' },
  sessionDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#ffffff88' },
  sessionDotActive: { backgroundColor: '#FCA5A5' },
  sessionButtonText: { color: '#fff', fontSize: 16, fontWeight: '800', letterSpacing: 0.2 },
  disabled: { opacity: 0.4 },

  inputDock: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    paddingHorizontal: 16, paddingBottom: 14,
  },
  input: {
    flex: 1, backgroundColor: '#111C33', color: '#F1F5F9', borderRadius: 14,
    borderWidth: 1, borderColor: '#233047', paddingHorizontal: 16, paddingVertical: 12, fontSize: 15,
  },
  sendButton: {
    backgroundColor: '#4F46E5', borderRadius: 14, paddingHorizontal: 20,
    paddingVertical: 13, alignItems: 'center', justifyContent: 'center',
  },
  sendButtonText: { color: '#fff', fontWeight: '800', fontSize: 15 },
});

// ---------------------------------------------------------------------------
// Root: SafeAreaProvider is required by useSafeAreaInsets
// ---------------------------------------------------------------------------

export default function Root() {
  return (
    <SafeAreaProvider>
      <App />
    </SafeAreaProvider>
  );
}
