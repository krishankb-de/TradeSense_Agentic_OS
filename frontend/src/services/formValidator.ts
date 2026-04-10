/**
 * Form Validator Service
 * Reusable validation logic for forms
 */

import { FormValidator, ValidationResult } from './types';

class FormValidatorImpl implements FormValidator {
  validateEmail(email: string): ValidationResult {
    if (!email || email.trim() === '') {
      return { isValid: false, error: 'Email is required' };
    }

    // RFC 5322 compliant email regex (simplified)
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    
    if (!emailRegex.test(email)) {
      return { isValid: false, error: 'Please enter a valid email address' };
    }

    return { isValid: true };
  }

  validatePassword(password: string): ValidationResult {
    if (!password || password.trim() === '') {
      return { isValid: false, error: 'Password is required' };
    }

    if (password.length < 8) {
      return { isValid: false, error: 'Password must be at least 8 characters' };
    }

    // Check for at least one letter and one number
    const hasLetter = /[a-zA-Z]/.test(password);
    const hasNumber = /[0-9]/.test(password);

    if (!hasLetter || !hasNumber) {
      return { 
        isValid: false, 
        error: 'Password must contain at least one letter and one number' 
      };
    }

    return { isValid: true };
  }

  validateRequired(value: any): ValidationResult {
    if (value === null || value === undefined) {
      return { isValid: false, error: 'This field is required' };
    }

    if (typeof value === 'string' && value.trim() === '') {
      return { isValid: false, error: 'This field is required' };
    }

    if (Array.isArray(value) && value.length === 0) {
      return { isValid: false, error: 'This field is required' };
    }

    return { isValid: true };
  }

  validatePhone(phone: string): ValidationResult {
    if (!phone || phone.trim() === '') {
      return { isValid: false, error: 'Phone number is required' };
    }

    // Remove all non-digit characters for validation
    const digitsOnly = phone.replace(/\D/g, '');

    // Check for valid US phone number (10 digits)
    if (digitsOnly.length !== 10) {
      return { 
        isValid: false, 
        error: 'Please enter a valid 10-digit phone number' 
      };
    }

    return { isValid: true };
  }

  validateLength(value: string, min: number, max: number): ValidationResult {
    if (!value) {
      return { isValid: false, error: 'This field is required' };
    }

    const length = value.trim().length;

    if (length < min) {
      return { 
        isValid: false, 
        error: `Must be at least ${min} characters` 
      };
    }

    if (length > max) {
      return { 
        isValid: false, 
        error: `Must be no more than ${max} characters` 
      };
    }

    return { isValid: true };
  }
}

// Export singleton instance
export const formValidator = new FormValidatorImpl();
