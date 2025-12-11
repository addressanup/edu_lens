/**
 * useDevice Hook
 * Convenience hook for accessing device state and actions
 */

import { useCallback } from 'react';
import {
  useDeviceStore,
  useDevices,
  useConnectedDevice,
  useDiscoveredDevices,
  useIsScanning,
  useDeviceError,
} from '../store/slices/deviceSlice';
import type { DeviceCommand, DeviceSettings, EduLensDevice } from '../types';

// ============================================================================
// useDevice Hook
// ============================================================================

export function useDevice() {
  // State selectors
  const devices = useDevices();
  const connectedDevice = useConnectedDevice();
  const discoveredDevices = useDiscoveredDevices();
  const isScanning = useIsScanning();
  const error = useDeviceError();

  // Additional state
  const isBluetoothEnabled = useDeviceStore((state) => state.isBluetoothEnabled);

  // Action selectors
  const startScan = useDeviceStore((state) => state.startScan);
  const stopScan = useDeviceStore((state) => state.stopScan);
  const connectDevice = useDeviceStore((state) => state.connectDevice);
  const disconnectDevice = useDeviceStore((state) => state.disconnectDevice);
  const pairDevice = useDeviceStore((state) => state.pairDevice);
  const unpairDevice = useDeviceStore((state) => state.unpairDevice);
  const sendCommand = useDeviceStore((state) => state.sendCommand);
  const updateDeviceSettings = useDeviceStore((state) => state.updateDeviceSettings);
  const refreshDeviceStatus = useDeviceStore((state) => state.refreshDeviceStatus);
  const checkFirmwareUpdate = useDeviceStore((state) => state.checkFirmwareUpdate);
  const updateFirmware = useDeviceStore((state) => state.updateFirmware);
  const clearError = useDeviceStore((state) => state.clearError);

  // ============================================================================
  // Wrapped Actions with Error Handling
  // ============================================================================

  const handleStartScan = useCallback(async (): Promise<boolean> => {
    try {
      await startScan();
      return true;
    } catch (error) {
      console.error('Scan failed:', error);
      return false;
    }
  }, [startScan]);

  const handleConnect = useCallback(
    async (deviceId: string): Promise<boolean> => {
      try {
        await connectDevice(deviceId);
        return true;
      } catch (error) {
        console.error('Connection failed:', error);
        return false;
      }
    },
    [connectDevice]
  );

  const handleDisconnect = useCallback(
    async (deviceId: string): Promise<boolean> => {
      try {
        await disconnectDevice(deviceId);
        return true;
      } catch (error) {
        console.error('Disconnection failed:', error);
        return false;
      }
    },
    [disconnectDevice]
  );

  const handlePairDevice = useCallback(
    async (deviceId: string, childId: string): Promise<boolean> => {
      try {
        await pairDevice(deviceId, childId);
        return true;
      } catch (error) {
        console.error('Pairing failed:', error);
        return false;
      }
    },
    [pairDevice]
  );

  const handleUnpairDevice = useCallback(
    async (deviceId: string): Promise<boolean> => {
      try {
        await unpairDevice(deviceId);
        return true;
      } catch (error) {
        console.error('Unpairing failed:', error);
        return false;
      }
    },
    [unpairDevice]
  );

  const handleSendCommand = useCallback(
    async (deviceId: string, command: DeviceCommand): Promise<boolean> => {
      try {
        await sendCommand(deviceId, command);
        return true;
      } catch (error) {
        console.error('Command failed:', error);
        return false;
      }
    },
    [sendCommand]
  );

  const handleUpdateSettings = useCallback(
    async (deviceId: string, settings: Partial<DeviceSettings>): Promise<boolean> => {
      try {
        await updateDeviceSettings(deviceId, settings);
        return true;
      } catch (error) {
        console.error('Settings update failed:', error);
        return false;
      }
    },
    [updateDeviceSettings]
  );

  const handleCheckUpdate = useCallback(
    async (deviceId: string): Promise<{ available: boolean; version?: string }> => {
      try {
        return await checkFirmwareUpdate(deviceId);
      } catch (error) {
        console.error('Update check failed:', error);
        return { available: false };
      }
    },
    [checkFirmwareUpdate]
  );

  const handleUpdateFirmware = useCallback(
    async (deviceId: string): Promise<boolean> => {
      try {
        await updateFirmware(deviceId);
        return true;
      } catch (error) {
        console.error('Firmware update failed:', error);
        return false;
      }
    },
    [updateFirmware]
  );

  // ============================================================================
  // Utility Functions
  // ============================================================================

  const getDeviceById = useCallback(
    (deviceId: string): EduLensDevice | undefined => {
      return devices.find((d) => d.id === deviceId);
    },
    [devices]
  );

  const getDeviceByChildId = useCallback(
    (childId: string): EduLensDevice | undefined => {
      return devices.find((d) => d.childId === childId);
    },
    [devices]
  );

  const getPairedDevices = useCallback((): EduLensDevice[] => {
    return devices.filter((d) => d.isPaired);
  }, [devices]);

  const isDeviceConnected = useCallback(
    (deviceId: string): boolean => {
      const device = devices.find((d) => d.id === deviceId);
      return device?.isConnected || false;
    },
    [devices]
  );

  const isDevicePaired = useCallback(
    (deviceId: string): boolean => {
      const device = devices.find((d) => d.id === deviceId);
      return device?.isPaired || false;
    },
    [devices]
  );

  const getBatteryLevel = useCallback(
    (deviceId: string): number | undefined => {
      const device = devices.find((d) => d.id === deviceId);
      return device?.batteryLevel;
    },
    [devices]
  );

  const needsBatteryCharge = useCallback(
    (deviceId: string, threshold: number = 20): boolean => {
      const batteryLevel = getBatteryLevel(deviceId);
      return batteryLevel !== undefined && batteryLevel < threshold;
    },
    [getBatteryLevel]
  );

  const hasActiveConnection = useCallback((): boolean => {
    return connectedDevice !== null;
  }, [connectedDevice]);

  const getConnectionStatus = useCallback(
    (deviceId: string): 'connected' | 'paired' | 'discovered' | 'offline' => {
      const device = devices.find((d) => d.id === deviceId);

      if (!device) {
        return discoveredDevices.some((d) => d.id === deviceId) ? 'discovered' : 'offline';
      }

      if (device.isConnected) return 'connected';
      if (device.isPaired) return 'paired';

      return 'offline';
    },
    [devices, discoveredDevices]
  );

  const canSendCommand = useCallback(
    (deviceId: string): boolean => {
      const device = devices.find((d) => d.id === deviceId);
      return device?.isConnected || false;
    },
    [devices]
  );

  // ============================================================================
  // Quick Actions
  // ============================================================================

  const setVolume = useCallback(
    async (deviceId: string, volume: number): Promise<boolean> => {
      return handleSendCommand(deviceId, {
        type: 'SET_VOLUME',
        payload: { volume },
      });
    },
    [handleSendCommand]
  );

  const setBrightness = useCallback(
    async (deviceId: string, brightness: number): Promise<boolean> => {
      return handleSendCommand(deviceId, {
        type: 'SET_BRIGHTNESS',
        payload: { brightness },
      });
    },
    [handleSendCommand]
  );

  const restartDevice = useCallback(
    async (deviceId: string): Promise<boolean> => {
      return handleSendCommand(deviceId, { type: 'RESTART' });
    },
    [handleSendCommand]
  );

  const enableFeature = useCallback(
    async (deviceId: string, feature: string): Promise<boolean> => {
      return handleSendCommand(deviceId, {
        type: 'ENABLE_FEATURE',
        payload: { feature },
      });
    },
    [handleSendCommand]
  );

  const disableFeature = useCallback(
    async (deviceId: string, feature: string): Promise<boolean> => {
      return handleSendCommand(deviceId, {
        type: 'DISABLE_FEATURE',
        payload: { feature },
      });
    },
    [handleSendCommand]
  );

  // ============================================================================
  // Return Hook API
  // ============================================================================

  return {
    // State
    devices,
    connectedDevice,
    discoveredDevices,
    isScanning,
    isBluetoothEnabled,
    error,

    // Actions
    startScan: handleStartScan,
    stopScan,
    connect: handleConnect,
    disconnect: handleDisconnect,
    pairDevice: handlePairDevice,
    unpairDevice: handleUnpairDevice,
    sendCommand: handleSendCommand,
    updateSettings: handleUpdateSettings,
    refreshStatus: refreshDeviceStatus,
    checkUpdate: handleCheckUpdate,
    updateFirmware: handleUpdateFirmware,
    clearError,

    // Utilities
    getDeviceById,
    getDeviceByChildId,
    getPairedDevices,
    isDeviceConnected,
    isDevicePaired,
    getBatteryLevel,
    needsBatteryCharge,
    hasActiveConnection,
    getConnectionStatus,
    canSendCommand,

    // Quick Actions
    setVolume,
    setBrightness,
    restartDevice,
    enableFeature,
    disableFeature,
  };
}

export default useDevice;
