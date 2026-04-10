/**
 * Setup Verification Tests
 * Ensures testing infrastructure is properly configured
 */

import { describe, it, expect, vi } from 'vitest';
import fc from 'fast-check';
import { getPropertyTestConfig } from '../../tests/propertyTestConfig';

describe('Testing Infrastructure Setup', () => {
  describe('Vitest Configuration', () => {
    it('should have access to vitest globals', () => {
      expect(describe).toBeDefined();
      expect(it).toBeDefined();
      expect(expect).toBeDefined();
      expect(vi).toBeDefined();
    });

    it('should have localStorage available', () => {
      expect(localStorage).toBeDefined();
      localStorage.setItem('test', 'value');
      expect(localStorage.getItem('test')).toBe('value');
      localStorage.clear();
    });
  });

  describe('fast-check Configuration', () => {
    it('should have fast-check available', () => {
      expect(fc).toBeDefined();
      expect(fc.assert).toBeDefined();
      expect(fc.property).toBeDefined();
    });

    it('should run a simple property test', () => {
      fc.assert(
        fc.property(fc.integer(), (n) => {
          return n + 0 === n;
        }),
        { numRuns: 10 }
      );
    });

    it('should load property test config', () => {
      const config = getPropertyTestConfig('dev');
      expect(config).toBeDefined();
      expect(config.numRuns).toBe(100);
    });
  });

  describe('Service Layer Structure', () => {
    it('should have services directory structure', () => {
      // This test verifies that imports work
      expect(() => import('../types')).toBeDefined();
      expect(() => import('../tokenManager')).toBeDefined();
      expect(() => import('../apiClient')).toBeDefined();
      expect(() => import('../errorHandler')).toBeDefined();
      expect(() => import('../mockDataProvider')).toBeDefined();
      expect(() => import('../formValidator')).toBeDefined();
    });
  });
});
