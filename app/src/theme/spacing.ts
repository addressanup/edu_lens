/**
 * Spacing system for EduLens App
 *
 * Based on 4px base unit for consistency
 */

export const spacing = {
  // Base unit
  unit: 4,

  // Named spacing values
  xxs: 2,
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
  xxxl: 64,

  // Specific use cases
  screenPadding: 16,
  cardPadding: 16,
  sectionGap: 24,
  itemGap: 12,
  iconGap: 8,

  // Border radius
  borderRadius: {
    sm: 4,
    md: 8,
    lg: 12,
    xl: 16,
    round: 9999,
  },
};

// Helper function to calculate spacing
export const space = (multiplier: number): number => spacing.unit * multiplier;
