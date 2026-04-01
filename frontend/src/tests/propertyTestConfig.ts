/**
 * fast-check configuration for TradeSense property-based testing.
 *
 * This module configures fast-check parameters for different testing scenarios:
 * - default: Standard testing with 1000 runs
 * - ci: Continuous integration with 500 runs for faster feedback
 * - thorough: Exhaustive testing with 5000 runs for critical properties
 * - dev: Development mode with 100 runs for quick iteration
 *
 * Usage:
 *   import { getPropertyTestConfig } from './propertyTestConfig';
 *   import fc from 'fast-check';
 *
 *   it('should satisfy property', () => {
 *     fc.assert(
 *       fc.property(someArb, (value) => {
 *         // property test
 *       }),
 *       getPropertyTestConfig('default')
 *     );
 *   });
 */

import fc from 'fast-check';

export type TestProfile = 'default' | 'ci' | 'thorough' | 'dev';

export interface PropertyTestConfig {
  numRuns: number;
  timeout?: number;
  verbose?: boolean;
  seed?: number;
  path?: string;
  endOnFailure?: boolean;
}

/**
 * Get fast-check configuration for a specific test profile.
 *
 * @param profile - The test profile to use (default, ci, thorough, dev)
 * @returns fast-check parameters for the specified profile
 */
export function getPropertyTestConfig(profile: TestProfile = 'default'): fc.Parameters<unknown> {
  const configs: Record<TestProfile, PropertyTestConfig> = {
    // Default profile: 1000 runs per property
    default: {
      numRuns: 1000,
      verbose: false,
      endOnFailure: true,
    },

    // CI profile: Faster testing for continuous integration
    ci: {
      numRuns: 500,
      timeout: 5000, // 5 second timeout
      verbose: false,
      endOnFailure: true,
    },

    // Thorough profile: Exhaustive testing for critical properties
    thorough: {
      numRuns: 5000,
      verbose: true,
      endOnFailure: false, // Continue to find all failures
    },

    // Development profile: Quick iteration during development
    dev: {
      numRuns: 100,
      timeout: 1000, // 1 second timeout
      verbose: false,
      endOnFailure: true,
    },
  };

  return configs[profile];
}

/**
 * Get the current test profile from environment variables.
 * Defaults to 'default' if not specified.
 *
 * Set via: TEST_PROFILE=thorough npm test
 */
export function getCurrentProfile(): TestProfile {
  const profile = process.env.TEST_PROFILE as TestProfile;
  return profile && ['default', 'ci', 'thorough', 'dev'].includes(profile) ? profile : 'default';
}

/**
 * Convenience function to get the current profile's configuration.
 */
export function getDefaultConfig(): fc.Parameters<unknown> {
  return getPropertyTestConfig(getCurrentProfile());
}

/**
 * Helper to create a property test with the default configuration.
 *
 * @param arb - The arbitrary to test
 * @param predicate - The property to verify
 * @param profile - Optional profile override
 */
export function assertProperty<T>(
  arb: fc.Arbitrary<T>,
  predicate: (value: T) => boolean | void,
  profile?: TestProfile
): void {
  fc.assert(fc.property(arb, predicate), getPropertyTestConfig(profile || getCurrentProfile()));
}

/**
 * Helper to create an async property test with the default configuration.
 *
 * @param arb - The arbitrary to test
 * @param predicate - The async property to verify
 * @param profile - Optional profile override
 */
export async function assertAsyncProperty<T>(
  arb: fc.Arbitrary<T>,
  predicate: (value: T) => Promise<boolean | void>,
  profile?: TestProfile
): Promise<void> {
  await fc.assert(fc.asyncProperty(arb, predicate), getPropertyTestConfig(profile || getCurrentProfile()));
}
