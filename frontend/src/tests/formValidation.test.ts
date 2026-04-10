/**
 * Unit tests for form validation edge cases
 * 
 * **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6**
 */

import { describe, it, expect } from 'vitest';
import { formValidator } from '../services/formValidator';

describe('FormValidator Edge Cases', () => {
  describe('Email Validation Edge Cases', () => {
    it('should reject email with spaces', () => {
      expect(formValidator.validateEmail('test @example.com').isValid).toBe(false);
      expect(formValidator.validateEmail('test@ example.com').isValid).toBe(false);
    });

    it('should reject email with multiple @ symbols', () => {
      expect(formValidator.validateEmail('test@@example.com').isValid).toBe(false);
    });

    it('should reject email without domain', () => {
      expect(formValidator.validateEmail('test@').isValid).toBe(false);
    });

    it('should reject email without username', () => {
      expect(formValidator.validateEmail('@example.com').isValid).toBe(false);
    });

    it('should accept email with plus sign', () => {
      expect(formValidator.validateEmail('test+tag@example.com').isValid).toBe(true);
    });

    it('should accept email with dots', () => {
      expect(formValidator.validateEmail('first.last@example.com').isValid).toBe(true);
    });

    it('should handle null and undefined', () => {
      expect(formValidator.validateEmail(null as any).isValid).toBe(false);
      expect(formValidator.validateEmail(undefined as any).isValid).toBe(false);
    });
  });

  describe('Password Validation Edge Cases', () => {
    it('should reject password with exactly 7 characters', () => {
      expect(formValidator.validatePassword('Pass123').isValid).toBe(false);
    });

    it('should accept password with exactly 8 characters', () => {
      expect(formValidator.validatePassword('Pass1234').isValid).toBe(true);
    });

    it('should reject password with only letters', () => {
      expect(formValidator.validatePassword('Password').isValid).toBe(false);
    });

    it('should reject password with only numbers', () => {
      expect(formValidator.validatePassword('12345678').isValid).toBe(false);
    });

    it('should accept password with special characters', () => {
      expect(formValidator.validatePassword('Pass123!@#').isValid).toBe(true);
    });

    it('should accept password with mixed case', () => {
      expect(formValidator.validatePassword('PaSsWoRd123').isValid).toBe(true);
    });

    it('should handle null and undefined', () => {
      expect(formValidator.validatePassword(null as any).isValid).toBe(false);
      expect(formValidator.validatePassword(undefined as any).isValid).toBe(false);
    });

    it('should trim whitespace before validation', () => {
      expect(formValidator.validatePassword('   ').isValid).toBe(false);
    });
  });

  describe('Required Field Validation Edge Cases', () => {
    it('should reject empty string', () => {
      expect(formValidator.validateRequired('').isValid).toBe(false);
    });

    it('should reject whitespace-only string', () => {
      expect(formValidator.validateRequired('   ').isValid).toBe(false);
      expect(formValidator.validateRequired('\t\n').isValid).toBe(false);
    });

    it('should accept string with content', () => {
      expect(formValidator.validateRequired('content').isValid).toBe(true);
    });

    it('should accept string with leading/trailing whitespace but content', () => {
      expect(formValidator.validateRequired('  content  ').isValid).toBe(true);
    });

    it('should reject null', () => {
      expect(formValidator.validateRequired(null).isValid).toBe(false);
    });

    it('should reject undefined', () => {
      expect(formValidator.validateRequired(undefined).isValid).toBe(false);
    });

    it('should reject empty array', () => {
      expect(formValidator.validateRequired([]).isValid).toBe(false);
    });

    it('should accept non-empty array', () => {
      expect(formValidator.validateRequired(['item']).isValid).toBe(true);
    });

    it('should accept number zero', () => {
      expect(formValidator.validateRequired(0).isValid).toBe(true);
    });

    it('should accept boolean false', () => {
      expect(formValidator.validateRequired(false).isValid).toBe(true);
    });
  });

  describe('Phone Validation Edge Cases', () => {
    it('should accept 10-digit phone number', () => {
      expect(formValidator.validatePhone('1234567890').isValid).toBe(true);
    });

    it('should accept formatted phone number', () => {
      expect(formValidator.validatePhone('(123) 456-7890').isValid).toBe(true);
    });

    it('should accept phone with dashes', () => {
      expect(formValidator.validatePhone('123-456-7890').isValid).toBe(true);
    });

    it('should accept phone with dots', () => {
      expect(formValidator.validatePhone('123.456.7890').isValid).toBe(true);
    });

    it('should reject phone with less than 10 digits', () => {
      expect(formValidator.validatePhone('123456789').isValid).toBe(false);
    });

    it('should reject phone with more than 10 digits', () => {
      expect(formValidator.validatePhone('12345678901').isValid).toBe(false);
    });

    it('should reject phone with letters', () => {
      expect(formValidator.validatePhone('123-abc-7890').isValid).toBe(false);
    });

    it('should handle null and undefined', () => {
      expect(formValidator.validatePhone(null as any).isValid).toBe(false);
      expect(formValidator.validatePhone(undefined as any).isValid).toBe(false);
    });
  });

  describe('Length Validation Edge Cases', () => {
    it('should accept string within range', () => {
      expect(formValidator.validateLength('hello', 3, 10).isValid).toBe(true);
    });

    it('should accept string at minimum length', () => {
      expect(formValidator.validateLength('abc', 3, 10).isValid).toBe(true);
    });

    it('should accept string at maximum length', () => {
      expect(formValidator.validateLength('abcdefghij', 3, 10).isValid).toBe(true);
    });

    it('should reject string below minimum', () => {
      expect(formValidator.validateLength('ab', 3, 10).isValid).toBe(false);
    });

    it('should reject string above maximum', () => {
      expect(formValidator.validateLength('abcdefghijk', 3, 10).isValid).toBe(false);
    });

    it('should trim whitespace before checking length', () => {
      expect(formValidator.validateLength('  abc  ', 3, 10).isValid).toBe(true);
    });

    it('should reject empty string', () => {
      expect(formValidator.validateLength('', 3, 10).isValid).toBe(false);
    });

    it('should handle null and undefined', () => {
      expect(formValidator.validateLength(null as any, 3, 10).isValid).toBe(false);
      expect(formValidator.validateLength(undefined as any, 3, 10).isValid).toBe(false);
    });
  });

  describe('Validation Result Structure', () => {
    it('should return isValid and no error for valid input', () => {
      const result = formValidator.validateEmail('test@example.com');
      expect(result).toHaveProperty('isValid');
      expect(result.isValid).toBe(true);
      expect(result.error).toBeUndefined();
    });

    it('should return isValid and error message for invalid input', () => {
      const result = formValidator.validateEmail('invalid');
      expect(result).toHaveProperty('isValid');
      expect(result).toHaveProperty('error');
      expect(result.isValid).toBe(false);
      expect(typeof result.error).toBe('string');
      expect(result.error!.length).toBeGreaterThan(0);
    });
  });
});
