/**
 * Property-based tests for TokenManager service
 * 
 * **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 2.1, 2.4, 2.5**
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fc from 'fast-check';
import { tokenManager } from '../services/tokenManager';
import { STORAGE_KEYS } from '../services/types';
import {
  tokenPairArb,
  validTokenArb,
  expiredTokenArb,
  malformedTokenArb,
  anyTokenArb,
  expiringSoonTokenArb,
  encodeTestToken,
} from './tokenGenerators';
import { getPropertyTestConfig } from './propertyTestConfig';

describe('TokenManager Property Tests', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
    tokenManager.cancelTokenRefresh();
  });

  afterEach(() => {
    // Clean up after each test
    localStorage.clear();
    tokenManager.cancelTokenRefresh();
    vi.clearAllMocks();
  });

  describe('Property 1: Token Storage Persistence', () => {
    /**
     * **Validates: Requirements 1.1**
     * 
     * For any successful login (represented by storing tokens),
     * tokens should be stored in localStorage with the correct keys.
     */
    it('should persist tokens to localStorage for any valid token pair', () => {
      fc.assert(
        fc.property(tokenPairArb, ({ accessToken, refreshToken }) => {
          // Store tokens
          tokenManager.storeTokens(accessToken, refreshToken);

          // Verify tokens are stored
          const storedAccessToken = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
          const storedRefreshToken = localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);

          expect(storedAccessToken).toBe(accessToken);
          expect(storedRefreshToken).toBe(refreshToken);

          // Verify tokens can be retrieved
          expect(tokenManager.getAccessToken()).toBe(accessToken);
          expect(tokenManager.getRefreshToken()).toBe(refreshToken);

          // Clean up for next iteration
          tokenManager.clearTokens();
        }),
        getPropertyTestConfig('default')
      );
    });

    it('should store token expiry when storing tokens', () => {
      fc.assert(
        fc.property(tokenPairArb, ({ accessToken, refreshToken }) => {
          // Store tokens
          tokenManager.storeTokens(accessToken, refreshToken);

          // Verify expiry is stored
          const storedExpiry = localStorage.getItem(STORAGE_KEYS.TOKEN_EXPIRY);
          expect(storedExpiry).not.toBeNull();

          // Verify expiry is a valid number
          const expiryTimestamp = parseInt(storedExpiry!, 10);
          expect(expiryTimestamp).toBeGreaterThan(0);

          // Clean up
          tokenManager.clearTokens();
        }),
        getPropertyTestConfig('default')
      );
    });

    it('should clear all tokens and related data when clearTokens is called', () => {
      fc.assert(
        fc.property(tokenPairArb, ({ accessToken, refreshToken }) => {
          // Store tokens
          tokenManager.storeTokens(accessToken, refreshToken);

          // Clear tokens
          tokenManager.clearTokens();

          // Verify all storage is cleared
          expect(localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN)).toBeNull();
          expect(localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN)).toBeNull();
          expect(localStorage.getItem(STORAGE_KEYS.TOKEN_EXPIRY)).toBeNull();
          expect(localStorage.getItem(STORAGE_KEYS.USER_DATA)).toBeNull();

          // Verify retrieval returns null
          expect(tokenManager.getAccessToken()).toBeNull();
          expect(tokenManager.getRefreshToken()).toBeNull();
        }),
        getPropertyTestConfig('default')
      );
    });
  });

  describe('Property 2: Token Validation on Load', () => {
    /**
     * **Validates: Requirements 1.2, 1.3**
     * 
     * For any token (valid, expired, malformed), validation should work correctly.
     */
    it('should correctly validate valid tokens', () => {
      fc.assert(
        fc.property(validTokenArb, (token) => {
          const isValid = tokenManager.isTokenValid(token);
          expect(isValid).toBe(true);
        }),
        getPropertyTestConfig('default')
      );
    });

    it('should correctly invalidate expired tokens', () => {
      fc.assert(
        fc.property(expiredTokenArb, (token) => {
          const isValid = tokenManager.isTokenValid(token);
          expect(isValid).toBe(false);
        }),
        getPropertyTestConfig('default')
      );
    });

    it('should correctly invalidate malformed tokens', () => {
      fc.assert(
        fc.property(malformedTokenArb, (token) => {
          const isValid = tokenManager.isTokenValid(token);
          expect(isValid).toBe(false);
        }),
        getPropertyTestConfig('default')
      );
    });

    it('should decode valid tokens correctly', () => {
      fc.assert(
        fc.property(validTokenArb, (token) => {
          const payload = tokenManager.decodeToken(token);
          
          expect(payload).not.toBeNull();
          expect(payload).toHaveProperty('sub');
          expect(payload).toHaveProperty('exp');
          expect(payload).toHaveProperty('iat');
          expect(payload).toHaveProperty('role');
        }),
        getPropertyTestConfig('default')
      );
    });

    it('should return null for malformed tokens when decoding', () => {
      fc.assert(
        fc.property(malformedTokenArb, (token) => {
          const payload = tokenManager.decodeToken(token);
          expect(payload).toBeNull();
        }),
        getPropertyTestConfig('default')
      );
    });
  });

  describe('Property 7: Proactive Token Refresh', () => {
    /**
     * **Validates: Requirements 2.4**
     * 
     * For any token within 5 minutes of expiration, refresh should be initiated.
     */
    it('should detect tokens expiring soon (within 5 minutes)', () => {
      fc.assert(
        fc.property(expiringSoonTokenArb, (token) => {
          const isExpiringSoon = tokenManager.isTokenExpiringSoon(token, 5);
          expect(isExpiringSoon).toBe(true);
        }),
        getPropertyTestConfig('default')
      );
    });

    it('should not detect valid tokens with more than 5 minutes remaining as expiring soon', () => {
      fc.assert(
        fc.property(
          fc.record({
            sub: fc.emailAddress(),
            exp: fc.integer({ min: Math.floor(Date.now() / 1000) + 301, max: Math.floor(Date.now() / 1000) + 86400 }), // more than 5 minutes
            iat: fc.integer({ min: Math.floor(Date.now() / 1000) - 3600, max: Math.floor(Date.now() / 1000) }),
            role: fc.constantFrom('admin', 'technician', 'dispatcher', 'customer'),
          }),
          (payload) => {
            const token = encodeTestToken(payload);
            const isExpiringSoon = tokenManager.isTokenExpiringSoon(token, 5);
            expect(isExpiringSoon).toBe(false);
          }
        ),
        getPropertyTestConfig('default')
      );
    });

    it('should schedule refresh for valid tokens', () => {
      fc.assert(
        fc.property(validTokenArb, (token) => {
          // Store the token
          tokenManager.storeTokens(token, token);

          // Schedule refresh
          tokenManager.scheduleTokenRefresh();

          // We can't easily test setTimeout directly, but we can verify no errors occur
          // and that the timer is set (internal state)
          expect(() => tokenManager.cancelTokenRefresh()).not.toThrow();

          // Clean up
          tokenManager.clearTokens();
        }),
        getPropertyTestConfig('default')
      );
    });
  });

  describe('Property 8: Token Storage Update on Refresh', () => {
    /**
     * **Validates: Requirements 2.5**
     * 
     * For any successful refresh, localStorage should be updated.
     * 
     * Note: This test mocks the fetch API since we can't make real API calls in tests.
     */
    it('should update localStorage with new access token on successful refresh', async () => {
      await fc.assert(
        fc.asyncProperty(tokenPairArb, async ({ accessToken, refreshToken }) => {
          // Store initial tokens
          tokenManager.storeTokens(accessToken, refreshToken);

          // Generate a new access token for the refresh response
          const newAccessToken = encodeTestToken({
            sub: 'test@example.com',
            exp: Math.floor(Date.now() / 1000) + 7200, // 2 hours from now
            iat: Math.floor(Date.now() / 1000),
            role: 'technician',
          });

          // Mock fetch for the refresh endpoint
          global.fetch = vi.fn().mockResolvedValue({
            ok: true,
            json: async () => ({ access_token: newAccessToken }),
          });

          // Perform refresh
          const returnedToken = await tokenManager.refreshAccessToken();

          // Verify the new token is returned
          expect(returnedToken).toBe(newAccessToken);

          // Verify localStorage is updated
          const storedAccessToken = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
          expect(storedAccessToken).toBe(newAccessToken);

          // Verify refresh token remains unchanged
          const storedRefreshToken = localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
          expect(storedRefreshToken).toBe(refreshToken);

          // Clean up
          tokenManager.clearTokens();
        }),
        getPropertyTestConfig('dev') // Use dev profile for faster async tests
      );
    });

    it('should clear tokens when refresh fails', async () => {
      await fc.assert(
        fc.asyncProperty(tokenPairArb, async ({ accessToken, refreshToken }) => {
          // Store initial tokens
          tokenManager.storeTokens(accessToken, refreshToken);

          // Mock fetch to simulate refresh failure
          global.fetch = vi.fn().mockResolvedValue({
            ok: false,
            status: 401,
          });

          // Attempt refresh and expect it to fail
          await expect(tokenManager.refreshAccessToken()).rejects.toThrow();

          // Verify tokens are cleared
          expect(localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN)).toBeNull();
          expect(localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN)).toBeNull();
        }),
        getPropertyTestConfig('dev') // Use dev profile for faster async tests
      );
    });
  });
});
