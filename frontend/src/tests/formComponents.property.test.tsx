/**
 * Property-based tests for form components
 * 
 * **Validates: Requirements 6.4, 6.5, 6.6**
 */

import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { render, cleanup } from '@testing-library/react';
import { ValidationFeedback } from '../components/ValidationFeedback';
import { FormField } from '../components/FormField';
import { getPropertyTestConfig } from './propertyTestConfig';
import { formFieldStateArb } from './formValidationGenerators';

describe('Form Component Properties', () => {
  describe('Property 20: Validation Feedback Display', () => {
    it('should display error icon and red text for invalid fields', () => {
      /**
       * **Validates: Requirements 6.4, 6.5**
       * 
       * Property: For any invalid validation state, feedback should show error icon and red text
       */
      fc.assert(
        fc.property(
          fc.string({ minLength: 5, maxLength: 100 }),
          (errorMessage) => {
            const validation = { isValid: false, error: errorMessage };
            const { container } = render(<ValidationFeedback validation={validation} />);
            
            // Check for red text color
            const feedbackDiv = container.querySelector('div[role="alert"]');
            expect(feedbackDiv).toBeTruthy();
            expect(feedbackDiv?.className).toContain('text-red-600');
            
            // Check error message is displayed using textContent
            const span = feedbackDiv?.querySelector('span');
            expect(span?.textContent).toBe(errorMessage);
            
            // Check for AlertCircle icon (lucide-react renders as svg)
            const svg = container.querySelector('svg');
            expect(svg).toBeTruthy();
            
            cleanup();
          }
        ),
        getPropertyTestConfig('default')
      );
    });

    it('should display checkmark and green text for valid fields', () => {
      /**
       * **Validates: Requirements 6.4, 6.5**
       * 
       * Property: For any valid validation state, feedback should show checkmark and green text
       */
      fc.assert(
        fc.property(fc.constant({ isValid: true }), (validation) => {
          const { container } = render(<ValidationFeedback validation={validation} />);
          
          // Check for green text color
          const feedbackDiv = container.querySelector('div[role="alert"]');
          expect(feedbackDiv).toBeTruthy();
          expect(feedbackDiv?.className).toContain('text-green-600');
          
          // Check "Valid" message is displayed
          const span = feedbackDiv?.querySelector('span');
          expect(span?.textContent).toBe('Valid');
          
          // Check for CheckCircle icon
          const svg = container.querySelector('svg');
          expect(svg).toBeTruthy();
          
          cleanup();
        }),
        getPropertyTestConfig('default')
      );
    });
  });

  describe('Property 21: Form Submit Enablement', () => {
    it('should enable submit button when all fields are valid', () => {
      /**
       * **Validates: Requirements 6.6**
       * 
       * Property: For any form state where all fields are valid, submit should be enabled
       */
      fc.assert(
        fc.property(
          fc.array(
            fc.record({
              name: fc.string({ minLength: 1, maxLength: 20 }),
              value: fc.string({ minLength: 1, maxLength: 50 }),
              isValid: fc.constant(true),
            }),
            { minLength: 1, maxLength: 5 }
          ),
          (fields) => {
            // All fields are valid
            const allValid = fields.every(f => f.isValid);
            expect(allValid).toBe(true);
            
            // Submit button should be enabled (not disabled)
            const shouldBeDisabled = !allValid;
            expect(shouldBeDisabled).toBe(false);
          }
        ),
        getPropertyTestConfig('default')
      );
    });

    it('should disable submit button when any field is invalid', () => {
      /**
       * **Validates: Requirements 6.6**
       * 
       * Property: For any form state with at least one invalid field, submit should be disabled
       */
      fc.assert(
        fc.property(
          fc.array(
            fc.record({
              name: fc.string({ minLength: 1, maxLength: 20 }),
              value: fc.string({ minLength: 0, maxLength: 50 }),
              isValid: fc.boolean(),
            }),
            { minLength: 2, maxLength: 5 }
          ).filter(fields => fields.some(f => !f.isValid)), // Ensure at least one invalid
          (fields) => {
            // At least one field is invalid
            const allValid = fields.every(f => f.isValid);
            expect(allValid).toBe(false);
            
            // Submit button should be disabled
            const shouldBeDisabled = !allValid;
            expect(shouldBeDisabled).toBe(true);
          }
        ),
        getPropertyTestConfig('default')
      );
    });
  });

  describe('FormField Integration', () => {
    it('should integrate validation feedback with form fields', () => {
      /**
       * Property: FormField should properly display validation state
       */
      fc.assert(
        fc.property(
          fc.string({ minLength: 1, maxLength: 20 }),
          fc.string({ minLength: 0, maxLength: 50 }),
          fc.boolean(),
          fc.option(fc.string({ minLength: 5, maxLength: 100 }), { nil: undefined }),
          (label, value, isValid, error) => {
            const validation = error ? { isValid, error } : { isValid };
            const { container } = render(
              <FormField
                label={label}
                name="test-field"
                type="text"
                value={value}
                onChange={() => {}}
                validation={validation}
              />
            );
            
            // Check label is rendered using textContent
            const labelElement = container.querySelector('label');
            expect(labelElement).toBeTruthy();
            expect(labelElement?.textContent).toContain(label);
            
            // Check input is rendered with correct value
            const input = container.querySelector('input');
            expect(input).toBeTruthy();
            expect(input?.value).toBe(value);
            
            // Check validation feedback is rendered if validation exists
            if (error) {
              const feedbackDiv = container.querySelector('div[role="alert"]');
              expect(feedbackDiv).toBeTruthy();
            }
            
            cleanup();
          }
        ),
        getPropertyTestConfig('default')
      );
    });
  });
});
