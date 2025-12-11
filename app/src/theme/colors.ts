/**
 * Color palette for EduLens App
 *
 * Colors are designed to be:
 * - Friendly and approachable for parents
 * - Accessible (WCAG AA compliant)
 * - Consistent across the app
 */

export const colors = {
  // Primary brand colors
  primary: {
    main: '#4A90A4',      // Teal - trust, education
    light: '#7BB5C5',
    dark: '#2D6B7D',
    contrast: '#FFFFFF',
  },

  // Secondary colors
  secondary: {
    main: '#F5A623',      // Orange - energy, enthusiasm
    light: '#FFCB6B',
    dark: '#C77800',
    contrast: '#FFFFFF',
  },

  // Accent colors for subjects
  subjects: {
    math: '#E74C3C',       // Red
    reading: '#9B59B6',    // Purple
    science: '#27AE60',    // Green
    socialStudies: '#3498DB', // Blue
  },

  // Status colors
  success: {
    main: '#27AE60',
    light: '#A9DFBF',
    dark: '#1E8449',
  },
  warning: {
    main: '#F5A623',
    light: '#FCE4BB',
    dark: '#D4840A',
  },
  error: {
    main: '#E74C3C',
    light: '#F5B7B1',
    dark: '#C0392B',
  },
  info: {
    main: '#3498DB',
    light: '#AED6F1',
    dark: '#2471A3',
  },

  // Neutral colors
  neutral: {
    white: '#FFFFFF',
    background: '#F8FAFB',
    surface: '#FFFFFF',
    border: '#E5E5E5',
    divider: '#EEEEEE',
    disabled: '#CCCCCC',
    placeholder: '#999999',
    text: {
      primary: '#333333',
      secondary: '#666666',
      tertiary: '#999999',
      inverse: '#FFFFFF',
    },
  },

  // Battery indicator colors
  battery: {
    full: '#27AE60',
    medium: '#F5A623',
    low: '#E74C3C',
    charging: '#3498DB',
  },

  // Connection status
  connection: {
    connected: '#27AE60',
    connecting: '#F5A623',
    disconnected: '#E74C3C',
  },
};

// Type for accessing colors
export type ColorPalette = typeof colors;
