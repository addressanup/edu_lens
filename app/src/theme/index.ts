/**
 * Theme exports for EduLens App
 */

export { colors } from './colors';
export type { ColorPalette } from './colors';

export { spacing, space } from './spacing';

export {
  fontFamily,
  fontSize,
  lineHeight,
  fontWeight,
  typography,
} from './typography';

// Combined theme object
export const theme = {
  colors: require('./colors').colors,
  spacing: require('./spacing').spacing,
  typography: require('./typography').typography,
};
