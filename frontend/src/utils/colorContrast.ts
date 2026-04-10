/**
 * Color Contrast Utilities
 * Ensures WCAG 2.1 AA compliance (4.5:1 ratio for normal text)
 */

/**
 * Convert hex color to RGB
 */
function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16),
      }
    : null;
}

/**
 * Calculate relative luminance
 * https://www.w3.org/TR/WCAG20-TECHS/G17.html
 */
function getLuminance(r: number, g: number, b: number): number {
  const [rs, gs, bs] = [r, g, b].map((c) => {
    const sRGB = c / 255;
    return sRGB <= 0.03928 ? sRGB / 12.92 : Math.pow((sRGB + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

/**
 * Calculate contrast ratio between two colors
 * Returns a value between 1 and 21
 */
export function getContrastRatio(color1: string, color2: string): number {
  const rgb1 = hexToRgb(color1);
  const rgb2 = hexToRgb(color2);

  if (!rgb1 || !rgb2) {
    throw new Error('Invalid color format. Use hex format (#RRGGBB)');
  }

  const lum1 = getLuminance(rgb1.r, rgb1.g, rgb1.b);
  const lum2 = getLuminance(rgb2.r, rgb2.g, rgb2.b);

  const lighter = Math.max(lum1, lum2);
  const darker = Math.min(lum1, lum2);

  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Check if contrast ratio meets WCAG AA standard (4.5:1 for normal text)
 */
export function meetsWCAGAA(color1: string, color2: string): boolean {
  return getContrastRatio(color1, color2) >= 4.5;
}

/**
 * Check if contrast ratio meets WCAG AAA standard (7:1 for normal text)
 */
export function meetsWCAGAAA(color1: string, color2: string): boolean {
  return getContrastRatio(color1, color2) >= 7;
}

/**
 * Check if contrast ratio meets WCAG AA standard for large text (3:1)
 */
export function meetsWCAGAALargeText(color1: string, color2: string): boolean {
  return getContrastRatio(color1, color2) >= 3;
}

/**
 * Color palette contrast verification
 * All text colors against their typical backgrounds
 */
export const colorContrastAudit = {
  // Primary text on white background
  primaryOnWhite: {
    foreground: '#2563eb', // primary-600
    background: '#ffffff',
    ratio: getContrastRatio('#2563eb', '#ffffff'),
    passes: meetsWCAGAA('#2563eb', '#ffffff'),
  },
  
  // Gray text on white background
  grayOnWhite: {
    foreground: '#4b5563', // gray-600
    background: '#ffffff',
    ratio: getContrastRatio('#4b5563', '#ffffff'),
    passes: meetsWCAGAA('#4b5563', '#ffffff'),
  },
  
  // Dark gray text on white background
  darkGrayOnWhite: {
    foreground: '#111827', // gray-900
    background: '#ffffff',
    ratio: getContrastRatio('#111827', '#ffffff'),
    passes: meetsWCAGAA('#111827', '#ffffff'),
  },
  
  // White text on primary background
  whiteOnPrimary: {
    foreground: '#ffffff',
    background: '#2563eb', // primary-600
    ratio: getContrastRatio('#ffffff', '#2563eb'),
    passes: meetsWCAGAA('#ffffff', '#2563eb'),
  },
  
  // White text on secondary background
  whiteOnSecondary: {
    foreground: '#ffffff',
    background: '#047857', // secondary-500 (darkened for WCAG AA)
    ratio: getContrastRatio('#ffffff', '#047857'),
    passes: meetsWCAGAA('#ffffff', '#047857'),
  },
  
  // Error text on white background
  errorOnWhite: {
    foreground: '#dc2626', // error (darkened for WCAG AA)
    background: '#ffffff',
    ratio: getContrastRatio('#dc2626', '#ffffff'),
    passes: meetsWCAGAA('#dc2626', '#ffffff'),
  },
  
  // Success text on white background
  successOnWhite: {
    foreground: '#047857', // success (darkened for WCAG AA)
    background: '#ffffff',
    ratio: getContrastRatio('#047857', '#ffffff'),
    passes: meetsWCAGAA('#047857', '#ffffff'),
  },
};

/**
 * Log contrast audit results to console
 */
export function logContrastAudit(): void {
  console.group('🎨 Color Contrast Audit (WCAG AA: 4.5:1)');
  
  Object.entries(colorContrastAudit).forEach(([key, value]) => {
    const status = value.passes ? '✅ PASS' : '❌ FAIL';
    console.log(
      `${status} ${key}: ${value.ratio.toFixed(2)}:1`,
      `(${value.foreground} on ${value.background})`
    );
  });
  
  console.groupEnd();
}
