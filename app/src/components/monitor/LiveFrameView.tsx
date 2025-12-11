/**
 * LiveFrameView Component
 *
 * Displays the live video frame from the glasses camera.
 */

import React from 'react';
import { View, Image, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { colors } from '../../theme/colors';
import { spacing } from '../../theme/spacing';

interface LiveFrameViewProps {
  frame: string | null;
  isConnected: boolean;
}

const LiveFrameView: React.FC<LiveFrameViewProps> = ({ frame, isConnected }) => {
  if (!isConnected) {
    return (
      <View style={styles.container}>
        <View style={styles.placeholder}>
          <Text style={styles.placeholderText}>Not Connected</Text>
        </View>
      </View>
    );
  }

  if (!frame) {
    return (
      <View style={styles.container}>
        <View style={styles.placeholder}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>Waiting for video...</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Image
        source={{ uri: frame }}
        style={styles.frame}
        resizeMode="contain"
      />
      <View style={styles.liveIndicator}>
        <View style={styles.liveDot} />
        <Text style={styles.liveText}>LIVE</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    margin: spacing.md,
    borderRadius: 12,
    overflow: 'hidden',
    backgroundColor: colors.cardBackground,
  },
  placeholder: {
    height: 200,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.background,
  },
  placeholderText: {
    fontSize: 16,
    color: colors.textSecondary,
  },
  loadingText: {
    fontSize: 14,
    color: colors.textSecondary,
    marginTop: spacing.sm,
  },
  frame: {
    width: '100%',
    height: 240,
    backgroundColor: colors.background,
  },
  liveIndicator: {
    position: 'absolute',
    top: spacing.sm,
    right: spacing.sm,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    borderRadius: 4,
  },
  liveDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#ff0000',
    marginRight: spacing.xs,
  },
  liveText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: colors.white,
  },
});

export default LiveFrameView;
