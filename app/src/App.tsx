/**
 * EduLens Parent Companion App
 *
 * React Native application for parents to:
 * - Monitor their child's learning progress
 * - Configure device settings and parental controls
 * - Pair with EduLens glasses via Bluetooth
 */

import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { AppNavigator } from './navigation/AppNavigator';
import { AuthProvider } from './auth/AuthContext';
import { BluetoothProvider } from './bluetooth/BluetoothContext';

export default function App(): React.JSX.Element {
  return (
    <SafeAreaProvider>
      <AuthProvider>
        <BluetoothProvider>
          <NavigationContainer>
            <AppNavigator />
          </NavigationContainer>
        </BluetoothProvider>
      </AuthProvider>
    </SafeAreaProvider>
  );
}
