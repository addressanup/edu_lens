/**
 * Device State Slice
 * Manages EduLens device state, pairing, connection, and settings
 * Handles both Bluetooth and WiFi connectivity
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';
import type {
  DeviceState,
  EduLensDevice,
  BluetoothScanResult,
  DeviceCommand,
  DeviceSettings,
  DeviceStatus,
} from '../../types';

// ============================================================================
// Device Slice Interface
// ============================================================================

interface DeviceSlice extends DeviceState {
  // Bluetooth scanning
  startScan: () => Promise<void>;
  stopScan: () => void;
  addDiscoveredDevice: (device: BluetoothScanResult) => void;
  clearDiscoveredDevices: () => void;

  // Device connection
  connectDevice: (deviceId: string) => Promise<void>;
  disconnectDevice: (deviceId: string) => Promise<void>;
  pairDevice: (deviceId: string, childId: string) => Promise<void>;
  unpairDevice: (deviceId: string) => Promise<void>;

  // Device management
  addDevice: (device: EduLensDevice) => void;
  updateDevice: (deviceId: string, updates: Partial<EduLensDevice>) => void;
  removeDevice: (deviceId: string) => void;
  refreshDeviceStatus: (deviceId: string) => Promise<void>;

  // Device commands
  sendCommand: (deviceId: string, command: DeviceCommand) => Promise<void>;
  updateDeviceSettings: (deviceId: string, settings: Partial<DeviceSettings>) => Promise<void>;

  // Firmware management
  checkFirmwareUpdate: (deviceId: string) => Promise<{ available: boolean; version?: string }>;
  updateFirmware: (deviceId: string) => Promise<void>;

  // State management
  setConnectedDevice: (device: EduLensDevice | null) => void;
  setBluetoothEnabled: (enabled: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
}

// ============================================================================
// Device Store Implementation
// ============================================================================

export const useDeviceStore = create<DeviceSlice>()(
  persist(
    (set, get) => ({
      // Initial state
      devices: [],
      connectedDevice: null,
      discoveredDevices: [],
      isScanning: false,
      isBluetoothEnabled: false,
      error: null,

      // ========================================================================
      // Bluetooth Scanning
      // ========================================================================
      startScan: async () => {
        if (get().isScanning) {
          return;
        }

        set({
          isScanning: true,
          discoveredDevices: [],
          error: null,
        });

        try {
          const { bluetoothService } = await import('../../services/bluetooth');
          await bluetoothService.startScan();

          // Auto-stop scan after 30 seconds
          setTimeout(() => {
            get().stopScan();
          }, 30000);
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to start scan';
          set({
            isScanning: false,
            error: errorMessage,
          });
          throw error;
        }
      },

      stopScan: () => {
        import('../../services/bluetooth').then(({ bluetoothService }) => {
          bluetoothService.stopScan();
        });

        set({ isScanning: false });
      },

      addDiscoveredDevice: (device: BluetoothScanResult) => {
        set((state) => {
          const exists = state.discoveredDevices.some((d) => d.id === device.id);

          if (exists) {
            // Update existing device (e.g., RSSI might have changed)
            return {
              discoveredDevices: state.discoveredDevices.map((d) =>
                d.id === device.id ? device : d
              ),
            };
          }

          // Add new device
          return {
            discoveredDevices: [...state.discoveredDevices, device],
          };
        });
      },

      clearDiscoveredDevices: () => {
        set({ discoveredDevices: [] });
      },

      // ========================================================================
      // Device Connection
      // ========================================================================
      connectDevice: async (deviceId: string) => {
        set({ error: null });

        try {
          const { bluetoothService } = await import('../../services/bluetooth');

          // Connect via Bluetooth
          await bluetoothService.connect(deviceId);

          // Fetch device details
          const { apiService } = await import('../../services/api');
          const response = await apiService.get<{ device: EduLensDevice }>(
            `/devices/${deviceId}`
          );

          if (response.success && response.data) {
            const device = {
              ...response.data.device,
              isConnected: true,
              connectionType: 'bluetooth' as const,
            };

            set((state) => ({
              connectedDevice: device,
              devices: state.devices.some((d) => d.id === deviceId)
                ? state.devices.map((d) => (d.id === deviceId ? device : d))
                : [...state.devices, device],
            }));

            // Start listening for device updates
            bluetoothService.subscribeToUpdates(deviceId, (status: DeviceStatus) => {
              get().updateDevice(deviceId, { status });
            });
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Connection failed';
          set({ error: errorMessage });
          throw error;
        }
      },

      disconnectDevice: async (deviceId: string) => {
        try {
          const { bluetoothService } = await import('../../services/bluetooth');
          await bluetoothService.disconnect(deviceId);

          set((state) => ({
            connectedDevice:
              state.connectedDevice?.id === deviceId ? null : state.connectedDevice,
            devices: state.devices.map((d) =>
              d.id === deviceId
                ? { ...d, isConnected: false, connectionType: 'offline' as const }
                : d
            ),
          }));
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Disconnection failed';
          set({ error: errorMessage });
          throw error;
        }
      },

      pairDevice: async (deviceId: string, childId: string) => {
        set({ error: null });

        try {
          const { apiService } = await import('../../services/api');

          const response = await apiService.post<{ device: EduLensDevice }>(
            `/devices/${deviceId}/pair`,
            { childId }
          );

          if (response.success && response.data) {
            const pairedDevice = { ...response.data.device, isPaired: true };

            set((state) => ({
              devices: state.devices.some((d) => d.id === deviceId)
                ? state.devices.map((d) => (d.id === deviceId ? pairedDevice : d))
                : [...state.devices, pairedDevice],
            }));
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Pairing failed';
          set({ error: errorMessage });
          throw error;
        }
      },

      unpairDevice: async (deviceId: string) => {
        try {
          const { apiService } = await import('../../services/api');
          await apiService.post(`/devices/${deviceId}/unpair`);

          set((state) => ({
            devices: state.devices.map((d) =>
              d.id === deviceId ? { ...d, isPaired: false, childId: undefined } : d
            ),
          }));
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Unpairing failed';
          set({ error: errorMessage });
          throw error;
        }
      },

      // ========================================================================
      // Device Management
      // ========================================================================
      addDevice: (device: EduLensDevice) => {
        set((state) => {
          const exists = state.devices.some((d) => d.id === device.id);
          if (exists) return state;

          return {
            devices: [...state.devices, device],
          };
        });
      },

      updateDevice: (deviceId: string, updates: Partial<EduLensDevice>) => {
        set((state) => ({
          devices: state.devices.map((d) =>
            d.id === deviceId ? { ...d, ...updates } : d
          ),
          connectedDevice:
            state.connectedDevice?.id === deviceId
              ? { ...state.connectedDevice, ...updates }
              : state.connectedDevice,
        }));
      },

      removeDevice: (deviceId: string) => {
        set((state) => ({
          devices: state.devices.filter((d) => d.id !== deviceId),
          connectedDevice:
            state.connectedDevice?.id === deviceId ? null : state.connectedDevice,
        }));
      },

      refreshDeviceStatus: async (deviceId: string) => {
        try {
          const { apiService } = await import('../../services/api');

          const response = await apiService.get<{ device: EduLensDevice }>(
            `/devices/${deviceId}`
          );

          if (response.success && response.data) {
            get().updateDevice(deviceId, response.data.device);
          }
        } catch (error) {
          console.error('Failed to refresh device status:', error);
        }
      },

      // ========================================================================
      // Device Commands
      // ========================================================================
      sendCommand: async (deviceId: string, command: DeviceCommand) => {
        const device = get().devices.find((d) => d.id === deviceId);

        if (!device) {
          throw new Error('Device not found');
        }

        try {
          if (device.isConnected && device.connectionType === 'bluetooth') {
            // Send via Bluetooth for immediate response
            const { bluetoothService } = await import('../../services/bluetooth');
            await bluetoothService.sendCommand(deviceId, command);
          } else {
            // Send via API (requires WiFi on device)
            const { apiService } = await import('../../services/api');
            await apiService.post(`/devices/${deviceId}/commands`, command);
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Command failed';
          set({ error: errorMessage });
          throw error;
        }
      },

      updateDeviceSettings: async (
        deviceId: string,
        settings: Partial<DeviceSettings>
      ) => {
        try {
          const { apiService } = await import('../../services/api');

          const response = await apiService.patch<{ device: EduLensDevice }>(
            `/devices/${deviceId}/settings`,
            settings
          );

          if (response.success && response.data) {
            get().updateDevice(deviceId, response.data.device);
          }

          // Also send command to device if connected
          const device = get().devices.find((d) => d.id === deviceId);
          if (device?.isConnected) {
            await get().sendCommand(deviceId, {
              type: 'ENABLE_FEATURE',
              payload: settings,
            });
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Settings update failed';
          set({ error: errorMessage });
          throw error;
        }
      },

      // ========================================================================
      // Firmware Management
      // ========================================================================
      checkFirmwareUpdate: async (deviceId: string) => {
        try {
          const { apiService } = await import('../../services/api');

          const response = await apiService.get<{
            available: boolean;
            version?: string;
            releaseNotes?: string;
          }>(`/devices/${deviceId}/firmware/check`);

          if (response.success && response.data) {
            return {
              available: response.data.available,
              version: response.data.version,
            };
          }

          return { available: false };
        } catch (error) {
          console.error('Firmware check failed:', error);
          return { available: false };
        }
      },

      updateFirmware: async (deviceId: string) => {
        const device = get().devices.find((d) => d.id === deviceId);

        if (!device?.isConnected) {
          throw new Error('Device must be connected to update firmware');
        }

        try {
          // Send firmware update command
          await get().sendCommand(deviceId, { type: 'UPDATE_FIRMWARE' });

          // The device will handle the update process
          // Monitor progress via device status updates
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Firmware update failed';
          set({ error: errorMessage });
          throw error;
        }
      },

      // ========================================================================
      // State Management
      // ========================================================================
      setConnectedDevice: (device: EduLensDevice | null) => {
        set({ connectedDevice: device });
      },

      setBluetoothEnabled: (enabled: boolean) => {
        set({ isBluetoothEnabled: enabled });
      },

      setError: (error: string | null) => {
        set({ error });
      },

      clearError: () => {
        set({ error: null });
      },
    }),
    {
      name: 'device-storage',
      storage: createJSONStorage(() => AsyncStorage),
      // Persist devices but not scanning/connection state
      partialize: (state) => ({
        devices: state.devices,
      }),
    }
  )
);

// ============================================================================
// Selector Hooks (for performance optimization)
// ============================================================================

export const useDevices = () => useDeviceStore((state) => state.devices);
export const useConnectedDevice = () => useDeviceStore((state) => state.connectedDevice);
export const useDiscoveredDevices = () => useDeviceStore((state) => state.discoveredDevices);
export const useIsScanning = () => useDeviceStore((state) => state.isScanning);
export const useDeviceError = () => useDeviceStore((state) => state.error);
