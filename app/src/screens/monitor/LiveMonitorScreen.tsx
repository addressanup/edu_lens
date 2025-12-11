/**
 * LiveMonitorScreen
 *
 * Main screen for parents to monitor their child's homework session
 * in real-time through the EduLens smart glasses.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  Alert,
  TouchableOpacity,
  TextInput,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useLiveMonitor, EncouragementType } from '../../hooks/useLiveMonitor';
import { useAuth } from '../../auth/AuthContext';
import { api } from '../../services/api';
import { colors } from '../../theme/colors';
import { spacing } from '../../theme/spacing';

// Components
import LiveFrameView from '../../components/monitor/LiveFrameView';
import ActivityFeed from '../../components/monitor/ActivityFeed';
import QuickActions from '../../components/monitor/QuickActions';
import ConnectionIndicator from '../../components/monitor/ConnectionIndicator';
import SessionStats from '../../components/monitor/SessionStats';

interface Session {
  session_id: string;
  child_id: string;
  state: string;
  frame_count: number;
}

const LiveMonitorScreen: React.FC = () => {
  const { children, selectedChild } = useAuth();

  // State
  const [availableSessions, setAvailableSessions] = useState<Session[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [messageText, setMessageText] = useState('');
  const [showMessageInput, setShowMessageInput] = useState(false);
  const [notifyChild, setNotifyChild] = useState(true);

  // Live monitor hook
  const {
    isConnected,
    connectionStatus,
    currentFrame,
    events,
    sessionStats,
    error,
    isLoading,
    startMonitoring,
    stopMonitoring,
    sendMessage,
    sendEncouragement,
    clearError,
  } = useLiveMonitor(selectedChild?.id);

  // Fetch available sessions
  const fetchSessions = useCallback(async () => {
    try {
      const response = await api.get('/api/v1/parent/sessions');
      const sessions = response.data.sessions || [];

      // Filter to only show sessions for the selected child
      const filtered = selectedChild
        ? sessions.filter((s: Session) => s.child_id === selectedChild.id)
        : sessions;

      setAvailableSessions(filtered);
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
    }
  }, [selectedChild]);

  useEffect(() => {
    fetchSessions();
    const interval = setInterval(fetchSessions, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, [fetchSessions]);

  // Handle connect
  const handleConnect = useCallback(async () => {
    if (!selectedSessionId) {
      Alert.alert('No Session', 'Please select a session to monitor');
      return;
    }

    await startMonitoring(selectedSessionId, notifyChild);
  }, [selectedSessionId, notifyChild, startMonitoring]);

  // Handle disconnect
  const handleDisconnect = useCallback(async () => {
    await stopMonitoring();
    setSelectedSessionId(null);
  }, [stopMonitoring]);

  // Handle send message
  const handleSendMessage = useCallback(() => {
    if (messageText.trim()) {
      sendMessage(messageText.trim());
      setMessageText('');
      setShowMessageInput(false);
    }
  }, [messageText, sendMessage]);

  // Handle encouragement
  const handleEncouragement = useCallback((type: EncouragementType) => {
    sendEncouragement(type);
  }, [sendEncouragement]);

  // Clear error on dismiss
  useEffect(() => {
    if (error) {
      Alert.alert('Error', error, [{ text: 'OK', onPress: clearError }]);
    }
  }, [error, clearError]);

  // Not connected view
  if (!isConnected) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.title}>Live Monitor</Text>
          <Text style={styles.subtitle}>
            Watch your child's homework session in real-time
          </Text>
        </View>

        <View style={styles.content}>
          {/* Child info */}
          {selectedChild && (
            <View style={styles.childInfo}>
              <Text style={styles.childName}>{selectedChild.name}</Text>
              <Text style={styles.childGrade}>Grade {selectedChild.grade}</Text>
            </View>
          )}

          {/* Available sessions */}
          <View style={styles.sessionsContainer}>
            <Text style={styles.sectionTitle}>Active Sessions</Text>

            {availableSessions.length === 0 ? (
              <View style={styles.noSessions}>
                <Text style={styles.noSessionsText}>
                  No active learning sessions
                </Text>
                <Text style={styles.noSessionsHint}>
                  When your child starts using EduLens glasses,
                  their session will appear here.
                </Text>
              </View>
            ) : (
              availableSessions.map((session) => (
                <TouchableOpacity
                  key={session.session_id}
                  style={[
                    styles.sessionItem,
                    selectedSessionId === session.session_id && styles.sessionItemSelected,
                  ]}
                  onPress={() => setSelectedSessionId(session.session_id)}
                >
                  <View style={styles.sessionInfo}>
                    <Text style={styles.sessionState}>
                      {session.state === 'observing' ? 'Active' : session.state}
                    </Text>
                    <Text style={styles.sessionFrames}>
                      {session.frame_count} frames
                    </Text>
                  </View>
                  <View style={styles.sessionIndicator}>
                    {session.state === 'observing' && (
                      <View style={styles.liveDot} />
                    )}
                  </View>
                </TouchableOpacity>
              ))
            )}
          </View>

          {/* Notification toggle */}
          <TouchableOpacity
            style={styles.toggleRow}
            onPress={() => setNotifyChild(!notifyChild)}
          >
            <Text style={styles.toggleLabel}>Notify child when watching</Text>
            <View style={[styles.toggle, notifyChild && styles.toggleActive]}>
              <View style={[styles.toggleThumb, notifyChild && styles.toggleThumbActive]} />
            </View>
          </TouchableOpacity>

          {/* Connect button */}
          <TouchableOpacity
            style={[
              styles.connectButton,
              (!selectedSessionId || isLoading) && styles.connectButtonDisabled,
            ]}
            onPress={handleConnect}
            disabled={!selectedSessionId || isLoading}
          >
            <Text style={styles.connectButtonText}>
              {isLoading ? 'Connecting...' : 'Start Monitoring'}
            </Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  // Connected view
  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardView}
      >
        {/* Header */}
        <View style={styles.connectedHeader}>
          <View style={styles.headerLeft}>
            <Text style={styles.connectedTitle}>Live Monitor</Text>
            {selectedChild && (
              <Text style={styles.connectedChild}>{selectedChild.name}</Text>
            )}
          </View>
          <ConnectionIndicator status={connectionStatus} />
        </View>

        <ScrollView style={styles.scrollContent}>
          {/* Live Frame */}
          <LiveFrameView
            frame={currentFrame}
            isConnected={isConnected}
          />

          {/* Session Stats */}
          <SessionStats stats={sessionStats} />

          {/* Activity Feed */}
          <ActivityFeed events={events} />
        </ScrollView>

        {/* Message Input */}
        {showMessageInput ? (
          <View style={styles.messageInputContainer}>
            <TextInput
              style={styles.messageInput}
              value={messageText}
              onChangeText={setMessageText}
              placeholder="Type a message to your child..."
              placeholderTextColor={colors.textSecondary}
              autoFocus
              onSubmitEditing={handleSendMessage}
            />
            <TouchableOpacity
              style={styles.sendButton}
              onPress={handleSendMessage}
            >
              <Text style={styles.sendButtonText}>Send</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.cancelButton}
              onPress={() => setShowMessageInput(false)}
            >
              <Text style={styles.cancelButtonText}>Cancel</Text>
            </TouchableOpacity>
          </View>
        ) : (
          /* Quick Actions */
          <QuickActions
            onEncouragement={handleEncouragement}
            onMessage={() => setShowMessageInput(true)}
            onDisconnect={handleDisconnect}
          />
        )}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  keyboardView: {
    flex: 1,
  },
  header: {
    padding: spacing.lg,
    backgroundColor: colors.primary,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: colors.white,
  },
  subtitle: {
    fontSize: 14,
    color: colors.white,
    opacity: 0.8,
    marginTop: spacing.xs,
  },
  content: {
    flex: 1,
    padding: spacing.lg,
  },
  childInfo: {
    backgroundColor: colors.cardBackground,
    padding: spacing.md,
    borderRadius: 12,
    marginBottom: spacing.lg,
  },
  childName: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.text,
  },
  childGrade: {
    fontSize: 14,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
  sessionsContainer: {
    flex: 1,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
    marginBottom: spacing.md,
  },
  noSessions: {
    backgroundColor: colors.cardBackground,
    padding: spacing.xl,
    borderRadius: 12,
    alignItems: 'center',
  },
  noSessionsText: {
    fontSize: 16,
    fontWeight: '500',
    color: colors.textSecondary,
    marginBottom: spacing.sm,
  },
  noSessionsHint: {
    fontSize: 14,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 20,
  },
  sessionItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: colors.cardBackground,
    padding: spacing.md,
    borderRadius: 12,
    marginBottom: spacing.sm,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  sessionItemSelected: {
    borderColor: colors.primary,
  },
  sessionInfo: {
    flex: 1,
  },
  sessionState: {
    fontSize: 16,
    fontWeight: '500',
    color: colors.text,
  },
  sessionFrames: {
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 2,
  },
  sessionIndicator: {
    width: 40,
    alignItems: 'center',
  },
  liveDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: colors.success,
  },
  toggleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.md,
    marginTop: spacing.lg,
  },
  toggleLabel: {
    fontSize: 16,
    color: colors.text,
  },
  toggle: {
    width: 50,
    height: 28,
    borderRadius: 14,
    backgroundColor: colors.border,
    padding: 2,
  },
  toggleActive: {
    backgroundColor: colors.primary,
  },
  toggleThumb: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: colors.white,
  },
  toggleThumbActive: {
    transform: [{ translateX: 22 }],
  },
  connectButton: {
    backgroundColor: colors.primary,
    padding: spacing.md,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: spacing.lg,
  },
  connectButtonDisabled: {
    backgroundColor: colors.border,
  },
  connectButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.white,
  },
  // Connected view styles
  connectedHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: spacing.md,
    backgroundColor: colors.primary,
  },
  headerLeft: {
    flex: 1,
  },
  connectedTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: colors.white,
  },
  connectedChild: {
    fontSize: 14,
    color: colors.white,
    opacity: 0.8,
  },
  scrollContent: {
    flex: 1,
  },
  messageInputContainer: {
    flexDirection: 'row',
    padding: spacing.md,
    backgroundColor: colors.cardBackground,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  messageInput: {
    flex: 1,
    backgroundColor: colors.background,
    borderRadius: 20,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    marginRight: spacing.sm,
    fontSize: 16,
    color: colors.text,
  },
  sendButton: {
    backgroundColor: colors.primary,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: 20,
    justifyContent: 'center',
  },
  sendButtonText: {
    color: colors.white,
    fontWeight: '600',
  },
  cancelButton: {
    paddingHorizontal: spacing.sm,
    justifyContent: 'center',
  },
  cancelButtonText: {
    color: colors.textSecondary,
  },
});

export default LiveMonitorScreen;
