/**
 * Bluetooth Service for EduLens Parent Companion App
 * Handles BLE communication with EduLens glasses
 */

import { BleManager, Device, State, Subscription } from 'react-native-ble-plx';
import type {
  BluetoothScanResult,
  DeviceCommand,
  DeviceStatus,
} from '../types';

// ============================================================================
// EduLens BLE Service UUIDs
// ============================================================================

const EDULENS_SERVICE_UUID = 'edu10001-0000-1000-8000-00805f9b34fb';
const EDULENS_COMMAND_CHAR_UUID = 'edu10002-0000-1000-8000-00805f9b34fb';
const EDULENS_STATUS_CHAR_UUID = 'edu10003-0000-1000-8000-00805f9b34fb';
const EDULENS_NOTIFICATION_CHAR_UUID = 'edu10004-0000-1000-8000-00805f9b34fb';
const EDULENS_BATTERY_CHAR_UUID = 'edu10005-0000-1000-8000-00805f9b34fb';

// ============================================================================
// Bluetooth Service Class
// ============================================================================

class BluetoothService {
  private manager: BleManager;
  private connectedDevices: Map<string, Device>;
  private scanSubscription: Subscription | null;
  private notificationSubscriptions: Map<string, Subscription>;
  private statusUpdateCallbacks: Map<string, (status: DeviceStatus) => void>;

  constructor() {
    this.manager = new BleManager();
    this.connectedDevices = new Map();
    this.scanSubscription = null;
    this.notificationSubscriptions = new Map();
    this.statusUpdateCallbacks = new Map();

    this.initialize();
  }

  // ==========================================================================
  // Initialization
  // ==========================================================================

  private async initialize(): Promise<void> {
    try {
      // Monitor Bluetooth state changes
      this.manager.onStateChange((state) => {
        this.handleStateChange(state);
      }, true);
    } catch (error) {
      console.error('Bluetooth initialization failed:', error);
    }
  }

  private async handleStateChange(state: State): Promise<void> {
    console.log('Bluetooth state changed:', state);

    // Update store with Bluetooth state
    const { useDeviceStore } = await import('../store/slices/deviceSlice');

    switch (state) {
      case 'PoweredOn':
        useDeviceStore.getState().setBluetoothEnabled(true);
        break;
      case 'PoweredOff':
      case 'Unauthorized':
      case 'Unsupported':
        useDeviceStore.getState().setBluetoothEnabled(false);
        break;
      default:
        break;
    }
  }

  // ==========================================================================
  // Device Scanning
  // ==========================================================================

  async startScan(): Promise<void> {
    try {
      // Check if Bluetooth is available
      const state = await this.manager.state();

      if (state !== 'PoweredOn') {
        throw new Error('Bluetooth is not enabled');
      }

      // Stop any existing scan
      if (this.scanSubscription) {
        this.stopScan();
      }

      const { useDeviceStore } = await import('../store/slices/deviceSlice');

      // Start scanning for EduLens devices
      this.scanSubscription = this.manager.startDeviceScan(
        [EDULENS_SERVICE_UUID],
        {
          allowDuplicates: false,
        },
        (error, device) => {
          if (error) {
            console.error('Scan error:', error);
            useDeviceStore.getState().setError(error.message);
            return;
          }

          if (device && device.name) {
            // Convert BLE device to scan result
            const scanResult: BluetoothScanResult = {
              id: device.id,
              name: device.name,
              rssi: device.rssi || -100,
              serviceUUIDs: device.serviceUUIDs || [],
              manufacturerData: device.manufacturerData,
              isConnectable: true,
            };

            // Add to discovered devices in store
            useDeviceStore.getState().addDiscoveredDevice(scanResult);
          }
        }
      );
    } catch (error) {
      console.error('Failed to start scan:', error);
      throw error;
    }
  }

  stopScan(): void {
    if (this.scanSubscription) {
      this.manager.stopDeviceScan();
      this.scanSubscription = null;
    }
  }

  // ==========================================================================
  // Device Connection
  // ==========================================================================

  async connect(deviceId: string): Promise<void> {
    try {
      // Check if already connected
      if (this.connectedDevices.has(deviceId)) {
        console.log('Device already connected:', deviceId);
        return;
      }

      // Stop scanning before connecting
      this.stopScan();

      // Connect to device
      const device = await this.manager.connectToDevice(deviceId, {
        timeout: 10000, // 10 second timeout
      });

      console.log('Connected to device:', device.name);

      // Discover services and characteristics
      await device.discoverAllServicesAndCharacteristics();

      // Store connected device
      this.connectedDevices.set(deviceId, device);

      // Setup notifications for device updates
      await this.setupNotifications(device);

      // Monitor disconnection
      device.onDisconnected((error) => {
        this.handleDisconnection(deviceId, error);
      });
    } catch (error) {
      console.error('Connection failed:', error);
      throw error;
    }
  }

  async disconnect(deviceId: string): Promise<void> {
    try {
      const device = this.connectedDevices.get(deviceId);

      if (!device) {
        console.warn('Device not found in connected devices:', deviceId);
        return;
      }

      // Unsubscribe from notifications
      const subscription = this.notificationSubscriptions.get(deviceId);
      if (subscription) {
        subscription.remove();
        this.notificationSubscriptions.delete(deviceId);
      }

      // Disconnect device
      await this.manager.cancelDeviceConnection(deviceId);

      // Remove from connected devices
      this.connectedDevices.delete(deviceId);
      this.statusUpdateCallbacks.delete(deviceId);

      console.log('Disconnected from device:', deviceId);
    } catch (error) {
      console.error('Disconnection failed:', error);
      throw error;
    }
  }

  private async handleDisconnection(deviceId: string, error: any): Promise<void> {
    console.log('Device disconnected:', deviceId, error);

    // Clean up
    this.connectedDevices.delete(deviceId);
    this.statusUpdateCallbacks.delete(deviceId);

    const subscription = this.notificationSubscriptions.get(deviceId);
    if (subscription) {
      subscription.remove();
      this.notificationSubscriptions.delete(deviceId);
    }

    // Update store
    const { useDeviceStore } = await import('../store/slices/deviceSlice');
    const state = useDeviceStore.getState();

    if (state.connectedDevice?.id === deviceId) {
      useDeviceStore.getState().setConnectedDevice(null);
    }
  }

  // ==========================================================================
  // Notifications
  // ==========================================================================

  private async setupNotifications(device: Device): Promise<void> {
    try {
      // Subscribe to device status notifications
      const subscription = device.monitorCharacteristicForService(
        EDULENS_SERVICE_UUID,
        EDULENS_NOTIFICATION_CHAR_UUID,
        (error, characteristic) => {
          if (error) {
            console.error('Notification error:', error);
            return;
          }

          if (characteristic?.value) {
            this.handleNotification(device.id, characteristic.value);
          }
        }
      );

      this.notificationSubscriptions.set(device.id, subscription);
    } catch (error) {
      console.error('Failed to setup notifications:', error);
    }
  }

  private handleNotification(deviceId: string, data: string): void {
    try {
      // Decode base64 data
      const decoded = Buffer.from(data, 'base64').toString('utf-8');
      const notification = JSON.parse(decoded);

      console.log('Received notification from device:', notification);

      // Handle different notification types
      if (notification.type === 'STATUS_UPDATE') {
        const callback = this.statusUpdateCallbacks.get(deviceId);
        if (callback) {
          callback(notification.status);
        }
      }
    } catch (error) {
      console.error('Failed to handle notification:', error);
    }
  }

  subscribeToUpdates(
    deviceId: string,
    callback: (status: DeviceStatus) => void
  ): void {
    this.statusUpdateCallbacks.set(deviceId, callback);
  }

  unsubscribeFromUpdates(deviceId: string): void {
    this.statusUpdateCallbacks.delete(deviceId);
  }

  // ==========================================================================
  // Device Communication
  // ==========================================================================

  async sendCommand(deviceId: string, command: DeviceCommand): Promise<void> {
    const device = this.connectedDevices.get(deviceId);

    if (!device) {
      throw new Error('Device not connected');
    }

    try {
      // Serialize command to JSON
      const commandJson = JSON.stringify(command);

      // Encode to base64
      const encoded = Buffer.from(commandJson).toString('base64');

      // Write to command characteristic
      await device.writeCharacteristicWithResponseForService(
        EDULENS_SERVICE_UUID,
        EDULENS_COMMAND_CHAR_UUID,
        encoded
      );

      console.log('Command sent successfully:', command.type);
    } catch (error) {
      console.error('Failed to send command:', error);
      throw error;
    }
  }

  async readStatus(deviceId: string): Promise<DeviceStatus> {
    const device = this.connectedDevices.get(deviceId);

    if (!device) {
      throw new Error('Device not connected');
    }

    try {
      // Read status characteristic
      const characteristic = await device.readCharacteristicForService(
        EDULENS_SERVICE_UUID,
        EDULENS_STATUS_CHAR_UUID
      );

      if (!characteristic.value) {
        throw new Error('No status data received');
      }

      // Decode base64 data
      const decoded = Buffer.from(characteristic.value, 'base64').toString('utf-8');
      const status: DeviceStatus = JSON.parse(decoded);

      return status;
    } catch (error) {
      console.error('Failed to read status:', error);
      throw error;
    }
  }

  async readBatteryLevel(deviceId: string): Promise<number> {
    const device = this.connectedDevices.get(deviceId);

    if (!device) {
      throw new Error('Device not connected');
    }

    try {
      const characteristic = await device.readCharacteristicForService(
        EDULENS_SERVICE_UUID,
        EDULENS_BATTERY_CHAR_UUID
      );

      if (!characteristic.value) {
        throw new Error('No battery data received');
      }

      // Battery level is a single byte (0-100)
      const buffer = Buffer.from(characteristic.value, 'base64');
      return buffer.readUInt8(0);
    } catch (error) {
      console.error('Failed to read battery level:', error);
      throw error;
    }
  }

  // ==========================================================================
  // Utility Methods
  // ==========================================================================

  isConnected(deviceId: string): boolean {
    return this.connectedDevices.has(deviceId);
  }

  getConnectedDevices(): string[] {
    return Array.from(this.connectedDevices.keys());
  }

  async isBluetoothEnabled(): Promise<boolean> {
    try {
      const state = await this.manager.state();
      return state === 'PoweredOn';
    } catch (error) {
      console.error('Failed to check Bluetooth state:', error);
      return false;
    }
  }

  async requestBluetoothPermission(): Promise<boolean> {
    try {
      // Request permission (handled by react-native-ble-plx)
      const state = await this.manager.state();
      return state === 'PoweredOn';
    } catch (error) {
      console.error('Permission request failed:', error);
      return false;
    }
  }

  // ==========================================================================
  // Cleanup
  // ==========================================================================

  async destroy(): Promise<void> {
    // Stop scanning
    this.stopScan();

    // Disconnect all devices
    const deviceIds = Array.from(this.connectedDevices.keys());
    for (const deviceId of deviceIds) {
      await this.disconnect(deviceId);
    }

    // Clear callbacks
    this.statusUpdateCallbacks.clear();

    // Destroy BLE manager
    await this.manager.destroy();
  }
}

// ============================================================================
// Singleton Export
// ============================================================================

export const bluetoothService = new BluetoothService();

export default bluetoothService;
