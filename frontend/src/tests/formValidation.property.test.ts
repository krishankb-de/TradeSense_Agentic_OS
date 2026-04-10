/**
 * Property-based tests for form validation
 * 
 * **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6**
 */

import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { formValidator } from '../services/formValidator';
import { getPropertyTestConfig } from './propertyTestConfig';
import {
  validEmailArb,
  invalidEmailArb,
  validPasswordArb,
  invalidPasswordArb,
  nonEmptyValueArb,
  emptyValueArb,
} from './formValidationGenerators';

describe('Form Validation Properties', () => {
  describe('Property 17: Email Validation', () => {
    it('should accept valid RFC 5322 compliant emails', () => {
      /**
       * **Validates: Requirements 6.1**
       * 
       * Property: For any valid email format, validation should pass
       */
      fc.assert(
        fc.property(validEmailArb, (email) => {
          const result = formValidator.validateEmail(email);
          expect(result.isValid).toBe(true);
          expect(result.error).toBeUndefined();
        }),
        getPropertyTestConfig('default')
      );
    });

    it('should reject invalid email formats', () => {
      /**
       * **Validates: Requirements 6.1**
       * 
       * Property: For any invalid email format, validation should fail with error message
       */
      fc.assert(
        fc.property(invalidEmailArb, (email) => {
          const result = formValidator.validateEmail(email);
          expect(result.isValid).toBe(false);
          expect(result.error).toBeDefined();
          expect(typeof result.error).toBe('string');
        }),
        getPropertyTestConfig('default')
      );
    });
  });

  describe('Property 18: Password Length Validation', () => {
    it('should accept passwords with >= 8 characters and letter+number', () => {
      /**
       * **Validates: Requirements 6.2**
       * 
       * Property: For any password >= 8 chars with letter and number, validation should pass
       */
      fc.assert(
        fc.property(validPasswordArb, (password) => {
          const result = formValidator.validatePassword(password);
          expect(result.isValid).toBe(true);
          expect(result.error).toBeUndefined();
        }),
        getPropertyTestConfig('default')
      );
    });

    it('should reject passwords < 8 characters or missing letter/number', () => {
      /**
       * **Validates: Requirements 6.2**
       * 
       * Property: For any password < 8 chars or missing letter/number, validation should fail
       */
      fc.assert(
        fc.property(invalidPasswordArb, (password) => {
          const result = formValidator.validatePassword(password);
          expect(result.isValid).toBe(false);
          expect(result.error).toBeDefined();
          expect(typeof result.error).toBe('string');
        }),
        getPropertyTestConfig('default')
      );
    });
  });

  describe('Property 19: Required Field Validation', () => {
    it('should accept non-empty values for required fields', () => {
      /**
       * **Validates: Requirements 6.3**
       * 
       * Property: For any non-empty value, required field validation should pass
       */
      fc.assert(
        fc.property(nonEmptyValueArb, (value) => {
          const result = formValidator.validateRequired(value);
          expect(result.isValid).toBe(true);
          expect(result.error).toBeUndefined();
        }),
        getPropertyTestConfig('default')
      );
    });

    it('should reject empty values for required fields', () => {
      /**
       * **Validates: Requirements 6.3**
       * 
       * Property: For any empty value, required field validation should fail
       */
      fc.assert(
        fc.property(emptyValueArb, (value) => {
          const result = formValidator.validateRequired(value);
          expect(result.isValid).toBe(false);
          expect(result.error).toBeDefined();
          expect(typeof result.error).toBe('string');
        }),
        getPropertyTestConfig('default')
      );
    });
  });
});
