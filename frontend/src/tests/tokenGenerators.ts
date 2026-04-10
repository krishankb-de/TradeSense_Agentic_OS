/**
 * Property-based test generators for JWT tokens and authentication.
 * 
 * This module provides fast-check arbitraries for generating valid and invalid
 * JWT tokens for testing the TokenManager service.
 */

import fc from 'fast-check';
import { TokenPayload } from '../services/types';

/**
 * Generate a valid JWT token payload.
 */
export const tokenPayloadArb: fc.Arbitrary<TokenPayload> = fc.record({
  sub: fc.emailAddress(),
  exp: fc.integer({ min: Math.floor(Date.now() / 1000) + 60, max: Math.floor(Date.now() / 1000) + 86400 }), // 1 minute to 24 hours from now
  iat: fc.integer({ min: Math.floor(Date.now() / 1000) - 3600, max: Math.floor(Date.now() / 1000) }), // up to 1 hour ago
  role: fc.constantFrom('admin', 'technician', 'dispatcher', 'customer'),
  jti: fc.option(fc.uuid(), { nil: undefined }),
});

/**
 * Generate an expired token payload.
 */
export const expiredTokenPayloadArb: fc.Arbitrary<TokenPayload> = fc.record({
  sub: fc.emailAddress(),
  exp: fc.integer({ min: Math.floor(Date.now() / 1000) - 86400, max: Math.floor(Date.now() / 1000) - 1 }), // expired
  iat: fc.integer({ min: Math.floor(Date.now() / 1000) - 90000, max: Math.floor(Date.now() / 1000) - 3600 }),
  role: fc.constantFrom('admin', 'technician', 'dispatcher', 'customer'),
  jti: fc.option(fc.uuid(), { nil: undefined }),
});

/**
 * Generate a token payload that expires soon (within 5 minutes).
 */
export const expiringSoonTokenPayloadArb: fc.Arbitrary<TokenPayload> = fc.record({
  sub: fc.emailAddress(),
  exp: fc.integer({ min: Math.floor(Date.now() / 1000) + 1, max: Math.floor(Date.now() / 1000) + 300 }), // 1-300 seconds from now
  iat: fc.integer({ min: Math.floor(Date.now() / 1000) - 3600, max: Math.floor(Date.now() / 1000) }),
  role: fc.constantFrom('admin', 'technician', 'dispatcher', 'customer'),
  jti: fc.option(fc.uuid(), { nil: undefined }),
});

/**
 * Encode a token payload into a JWT-like string (simplified, not cryptographically signed).
 * This is for testing purposes only.
 */
export function encodeTestToken(payload: TokenPayload): string {
  const header = { alg: 'HS256', typ: 'JWT' };
  const encodedHeader = btoa(JSON.stringify(header));
  const encodedPayload = btoa(JSON.stringify(payload));
  const signature = 'test-signature';
  return `${encodedHeader}.${encodedPayload}.${signature}`;
}

/**
 * Generate a valid JWT token string.
 */
export const validTokenArb: fc.Arbitrary<string> = tokenPayloadArb.map(encodeTestToken);

/**
 * Generate an expired JWT token string.
 */
export const expiredTokenArb: fc.Arbitrary<string> = expiredTokenPayloadArb.map(encodeTestToken);

/**
 * Generate a token that expires soon.
 */
export const expiringSoonTokenArb: fc.Arbitrary<string> = expiringSoonTokenPayloadArb.map(encodeTestToken);

/**
 * Generate a malformed JWT token string.
 */
export const malformedTokenArb: fc.Arbitrary<string> = fc.oneof(
  fc.string({ minLength: 10, maxLength: 50 }), // random string
  fc.constant('invalid.token'), // missing parts
  fc.constant(''), // empty string
  fc.constant('a.b.c.d'), // too many parts
);

/**
 * Generate any token (valid, expired, or malformed).
 */
export const anyTokenArb: fc.Arbitrary<string> = fc.oneof(
  validTokenArb,
  expiredTokenArb,
  malformedTokenArb
);

/**
 * Generate a pair of access and refresh tokens.
 */
export const tokenPairArb: fc.Arbitrary<{ accessToken: string; refreshToken: string }> = fc.record({
  accessToken: validTokenArb,
  refreshToken: validTokenArb,
});
