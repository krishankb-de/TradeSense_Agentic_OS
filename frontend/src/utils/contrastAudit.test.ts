/**
 * Color Contrast Audit Tests
 * Validates: Requirements 13.3
 */

import { describe, it, expect } from 'vitest';
import {
  getContrastRatio,
  meetsWCAGAA,
  colorContrastAudit,
  logContrastAudit,
} from './colorContrast';

describe('Color Contrast Utilities', () => {
  describe('getContrastRatio', () => {
    it('should calculate correct contrast ratio for black on white', () => {
      const ratio = getContrastRatio('#000000', '#ffffff');
      expect(ratio).toBeCloseTo(21, 1); // Maximum contrast
    });

    it('should calculate correct contrast ratio for white on black', () => {
      const ratio = getContrastRatio('#ffffff', '#000000');
      expect(ratio).toBeCloseTo(21, 1); // Same as black on white
    });

    it('should calculate correct contrast ratio for same colors', () => {
      const ratio = getContrastRatio('#ffffff', '#ffffff');
      expect(ratio).toBeCloseTo(1, 1); // Minimum contrast
    });
  });

  describe('meetsWCAGAA', () => {
    it('should pass for high contrast combinations', () => {
      expect(meetsWCAGAA('#000000', '#ffffff')).toBe(true);
      expect(meetsWCAGAA('#ffffff', '#000000')).toBe(true);
    });

    it('should fail for low contrast combinations', () => {
      expect(meetsWCAGAA('#ffffff', '#f0f0f0')).toBe(false);
      expect(meetsWCAGAA('#cccccc', '#ffffff')).toBe(false);
    });
  });

  describe('Color Palette Contrast Audit', () => {
    it('should have all text colors meet WCAG AA standards', () => {
      const failedTests: string[] = [];

      Object.entries(colorContrastAudit).forEach(([key, value]) => {
        if (!value.passes) {
          failedTests.push(
            `${key}: ${value.ratio.toFixed(2)}:1 (${value.foreground} on ${value.background})`
          );
        }
      });

      // Log audit results for visibility
      logContrastAudit();

      // Assert all tests pass
      expect(failedTests).toEqual([]);
    });

    it('should have primary text on white meet 4.5:1 ratio', () => {
      const { ratio, passes } = colorContrastAudit.primaryOnWhite;
      expect(ratio).toBeGreaterThanOrEqual(4.5);
      expect(passes).toBe(true);
    });

    it('should have gray text on white meet 4.5:1 ratio', () => {
      const { ratio, passes } = colorContrastAudit.grayOnWhite;
      expect(ratio).toBeGreaterThanOrEqual(4.5);
      expect(passes).toBe(true);
    });

    it('should have dark gray text on white meet 4.5:1 ratio', () => {
      const { ratio, passes } = colorContrastAudit.darkGrayOnWhite;
      expect(ratio).toBeGreaterThanOrEqual(4.5);
      expect(passes).toBe(true);
    });

    it('should have white text on primary background meet 4.5:1 ratio', () => {
      const { ratio, passes } = colorContrastAudit.whiteOnPrimary;
      expect(ratio).toBeGreaterThanOrEqual(4.5);
      expect(passes).toBe(true);
    });

    it('should have white text on secondary background meet 4.5:1 ratio', () => {
      const { ratio, passes } = colorContrastAudit.whiteOnSecondary;
      expect(ratio).toBeGreaterThanOrEqual(4.5);
      expect(passes).toBe(true);
    });

    it('should have error text on white meet 4.5:1 ratio', () => {
      const { ratio, passes } = colorContrastAudit.errorOnWhite;
      expect(ratio).toBeGreaterThanOrEqual(4.5);
      expect(passes).toBe(true);
    });

    it('should have success text on white meet 4.5:1 ratio', () => {
      const { ratio, passes } = colorContrastAudit.successOnWhite;
      expect(ratio).toBeGreaterThanOrEqual(4.5);
      expect(passes).toBe(true);
    });
  });
});
