/**
 * Main navigation structure for EduLens Parent Companion App
 */

import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';

// Screen imports
import LiveMonitorScreen from '../screens/monitor/LiveMonitorScreen';
// import { LoginScreen } from '../screens/LoginScreen';
// import { DashboardScreen } from '../screens/DashboardScreen';
// import { PairingScreen } from '../screens/PairingScreen';
// import { SettingsScreen } from '../screens/SettingsScreen';
// import { UsageLimitsScreen } from '../screens/UsageLimitsScreen';
// import { ContentFiltersScreen } from '../screens/ContentFiltersScreen';

export type RootStackParamList = {
  Auth: undefined;
  Main: undefined;
  Pairing: undefined;
};

export type AuthStackParamList = {
  Login: undefined;
  Register: undefined;
  ForgotPassword: undefined;
};

export type MainTabParamList = {
  Dashboard: undefined;
  Progress: undefined;
  LiveMonitor: undefined;
  Settings: undefined;
};

export type SettingsStackParamList = {
  SettingsHome: undefined;
  UsageLimits: undefined;
  ContentFilters: undefined;
  DeviceManagement: undefined;
  Account: undefined;
};

const RootStack = createNativeStackNavigator<RootStackParamList>();
const AuthStack = createNativeStackNavigator<AuthStackParamList>();
const MainTab = createBottomTabNavigator<MainTabParamList>();
const SettingsStack = createNativeStackNavigator<SettingsStackParamList>();

// Placeholder components until screens are implemented
const PlaceholderScreen = () => null;

function AuthNavigator() {
  return (
    <AuthStack.Navigator screenOptions={{ headerShown: false }}>
      <AuthStack.Screen name="Login" component={PlaceholderScreen} />
      <AuthStack.Screen name="Register" component={PlaceholderScreen} />
      <AuthStack.Screen name="ForgotPassword" component={PlaceholderScreen} />
    </AuthStack.Navigator>
  );
}

function SettingsNavigator() {
  return (
    <SettingsStack.Navigator>
      <SettingsStack.Screen
        name="SettingsHome"
        component={PlaceholderScreen}
        options={{ title: 'Settings' }}
      />
      <SettingsStack.Screen
        name="UsageLimits"
        component={PlaceholderScreen}
        options={{ title: 'Usage Limits' }}
      />
      <SettingsStack.Screen
        name="ContentFilters"
        component={PlaceholderScreen}
        options={{ title: 'Content Filters' }}
      />
      <SettingsStack.Screen
        name="DeviceManagement"
        component={PlaceholderScreen}
        options={{ title: 'Manage Devices' }}
      />
      <SettingsStack.Screen
        name="Account"
        component={PlaceholderScreen}
        options={{ title: 'Account' }}
      />
    </SettingsStack.Navigator>
  );
}

function MainNavigator() {
  return (
    <MainTab.Navigator>
      <MainTab.Screen
        name="Dashboard"
        component={PlaceholderScreen}
        options={{ title: 'Home' }}
      />
      <MainTab.Screen
        name="Progress"
        component={PlaceholderScreen}
        options={{ title: 'Progress' }}
      />
      <MainTab.Screen
        name="LiveMonitor"
        component={LiveMonitorScreen}
        options={{
          title: 'Live',
          headerShown: false,
        }}
      />
      <MainTab.Screen
        name="Settings"
        component={SettingsNavigator}
        options={{ headerShown: false }}
      />
    </MainTab.Navigator>
  );
}

export function AppNavigator() {
  // TODO: Check authentication state from AuthContext
  const isAuthenticated = false;

  return (
    <RootStack.Navigator screenOptions={{ headerShown: false }}>
      {!isAuthenticated ? (
        <RootStack.Screen name="Auth" component={AuthNavigator} />
      ) : (
        <>
          <RootStack.Screen name="Main" component={MainNavigator} />
          <RootStack.Screen
            name="Pairing"
            component={PlaceholderScreen}
            options={{ presentation: 'modal' }}
          />
        </>
      )}
    </RootStack.Navigator>
  );
}
