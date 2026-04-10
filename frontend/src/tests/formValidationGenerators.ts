/**
 * Property-based test generators for form validation
 */

import fc from 'fast-check';

/**
 * Generate valid email addresses (RFC 5322 compliant)
 */
export const validEmailArb = fc
  .tuple(
    fc.string({ minLength: 1, maxLength: 20 }).map(s => s.toLowerCase().replace(/[^a-z0-9]/g, 'a')),
    fc.string({ minLength: 2, maxLength: 15 }).map(s => s.toLowerCase().replace(/[^a-z]/g, 'a')),
    fc.constantFrom('com', 'org', 'net', 'io', 'dev', 'edu')
  )
  .map(([username, domain, tld]) => `${username}@${domain}.${tld}`);

/**
 * Generate invalid email addresses
 */
export const invalidEmailArb = fc.oneof(
  // Missing @
  fc.string({ minLength: 1, maxLength: 30 }).filter(s => !s.includes('@')),
  // Missing domain
  fc.string({ minLength: 1, maxLength: 20 }).map(s => `${s}@`),
  // Missing TLD
  fc.string({ minLength: 1, maxLength: 20 }).map(s => `${s}@domain`),
  // Just @
  fc.constant('@'),
  // Empty string
  fc.constant(''),
  // Whitespace only
  fc.constant('   '),
  // Multiple @
  fc.string({ minLength: 1, maxLength: 10 }).map(s => `${s}@@domain.com`)
);

/**
 * Generate valid passwords (>= 8 chars, at least one letter and one number)
 */
export const validPasswordArb = fc
  .tuple(
    fc.string({ minLength: 1, maxLength: 10 }).filter(s => /[a-zA-Z]/.test(s)),
    fc.string({ minLength: 1, maxLength: 10 }).filter(s => /[0-9]/.test(s)),
    fc.string({ minLength: 0, maxLength: 10 })
  )
  .map(([letters, numbers, extra]) => {
    const combined = letters + numbers + extra;
    // Ensure at least 8 characters
    return combined.length >= 8 ? combined : combined + 'a'.repeat(8 - combined.length);
  });

/**
 * Generate invalid passwords (< 8 chars or missing letter/number)
 */
export const invalidPasswordArb = fc.oneof(
  // Too short
  fc.string({ minLength: 0, maxLength: 7 }),
  // No numbers
  fc.string({ minLength: 8, maxLength: 20 }).filter(s => !/[0-9]/.test(s)),
  // No letters
  fc.string({ minLength: 8, maxLength: 20 }).filter(s => !/[a-zA-Z]/.test(s)),
  // Empty
  fc.constant(''),
  // Whitespace only
  fc.constant('        ')
);

/**
 * Generate non-empty values (valid for required fields)
 */
export const nonEmptyValueArb = fc.oneof(
  fc.string({ minLength: 1, maxLength: 100 }).filter(s => s.trim().length > 0),
  fc.integer({ min: 1, max: 1000 }),
  fc.boolean(),
  fc.array(fc.string(), { minLength: 1, maxLength: 10 })
);

/**
 * Generate empty values (invalid for required fields)
 */
export const emptyValueArb = fc.oneof(
  fc.constant(''),
  fc.constant('   '),
  fc.constant(null),
  fc.constant(undefined),
  fc.constant([])
);

/**
 * Generate valid phone numbers (10 digits)
 */
export const validPhoneArb = fc
  .tuple(
    fc.integer({ min: 200, max: 999 }),
    fc.integer({ min: 200, max: 999 }),
    fc.integer({ min: 1000, max: 9999 })
  )
  .map(([area, exchange, number]) => `(${area}) ${exchange}-${number}`);

/**
 * Generate invalid phone numbers
 */
export const invalidPhoneArb = fc.oneof(
  // Too short
  fc.string({ minLength: 1, maxLength: 9 }),
  // Too long
  fc.string({ minLength: 11, maxLength: 20 }),
  // Empty
  fc.constant(''),
  // Letters
  fc.constant('abc-def-ghij')
);

/**
 * Generate form field states for validation feedback testing
 */
export const formFieldStateArb = fc.record({
  value: fc.string({ minLength: 0, maxLength: 50 }),
  isValid: fc.boolean(),
  error: fc.option(fc.string({ minLength: 5, maxLength: 100 }), { nil: undefined }),
  touched: fc.boolean(),
});

/**
 * Generate form states with multiple fields
 */
export const formStateArb = fc.record({
  email: formFieldStateArb,
  password: formFieldStateArb,
  name: formFieldStateArb,
  allValid: fc.boolean(),
});
