/**
 * Typography system for EduLens App
 */

import { TextStyle } from 'react-native';

export const fontFamily = {
  regular: 'System',
  medium: 'System',
  semiBold: 'System',
  bold: 'System',
};

export const fontSize = {
  xs: 12,
  sm: 14,
  md: 16,
  lg: 18,
  xl: 20,
  xxl: 24,
  xxxl: 32,
  display: 40,
};

export const lineHeight = {
  xs: 16,
  sm: 20,
  md: 24,
  lg: 28,
  xl: 28,
  xxl: 32,
  xxxl: 40,
  display: 48,
};

export const fontWeight = {
  regular: '400' as TextStyle['fontWeight'],
  medium: '500' as TextStyle['fontWeight'],
  semiBold: '600' as TextStyle['fontWeight'],
  bold: '700' as TextStyle['fontWeight'],
};

// Pre-defined text styles
export const typography = {
  // Display styles
  displayLarge: {
    fontSize: fontSize.display,
    lineHeight: lineHeight.display,
    fontWeight: fontWeight.bold,
  } as TextStyle,

  displayMedium: {
    fontSize: fontSize.xxxl,
    lineHeight: lineHeight.xxxl,
    fontWeight: fontWeight.bold,
  } as TextStyle,

  // Heading styles
  h1: {
    fontSize: fontSize.xxl,
    lineHeight: lineHeight.xxl,
    fontWeight: fontWeight.bold,
  } as TextStyle,

  h2: {
    fontSize: fontSize.xl,
    lineHeight: lineHeight.xl,
    fontWeight: fontWeight.semiBold,
  } as TextStyle,

  h3: {
    fontSize: fontSize.lg,
    lineHeight: lineHeight.lg,
    fontWeight: fontWeight.semiBold,
  } as TextStyle,

  // Body styles
  bodyLarge: {
    fontSize: fontSize.md,
    lineHeight: lineHeight.md,
    fontWeight: fontWeight.regular,
  } as TextStyle,

  bodyMedium: {
    fontSize: fontSize.sm,
    lineHeight: lineHeight.sm,
    fontWeight: fontWeight.regular,
  } as TextStyle,

  bodySmall: {
    fontSize: fontSize.xs,
    lineHeight: lineHeight.xs,
    fontWeight: fontWeight.regular,
  } as TextStyle,

  // Label styles
  labelLarge: {
    fontSize: fontSize.md,
    lineHeight: lineHeight.md,
    fontWeight: fontWeight.semiBold,
  } as TextStyle,

  labelMedium: {
    fontSize: fontSize.sm,
    lineHeight: lineHeight.sm,
    fontWeight: fontWeight.semiBold,
  } as TextStyle,

  labelSmall: {
    fontSize: fontSize.xs,
    lineHeight: lineHeight.xs,
    fontWeight: fontWeight.semiBold,
  } as TextStyle,

  // Button text
  button: {
    fontSize: fontSize.md,
    lineHeight: lineHeight.md,
    fontWeight: fontWeight.semiBold,
  } as TextStyle,

  // Caption
  caption: {
    fontSize: fontSize.xs,
    lineHeight: lineHeight.xs,
    fontWeight: fontWeight.regular,
  } as TextStyle,
};
