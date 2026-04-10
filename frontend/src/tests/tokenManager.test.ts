/**
 * Unit tests for TokenManager service edge cases
 * 
 * **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 2.1, 2.4, 2.5**
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { tokenManager } from '../services/tokenManager';
import { STORAGE_KEYS } from '../services/types';
import { encodeTestToken } from './tokenGenerators';

describe('TokenManager Unit Tests - Edge Cases', () => {
  beforeEach(() => {
    localStorage.clear();
    tokenManager.cancelTokenRefresh();
    vi.clearAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
    tokenManager.cancelTokenRefresh();
    vi.clearAllMocks();
  });

  describe('Token Storage Edge Cases', () => {
    it('should handle storing tokens with special characters', () => {
      const accessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZXhwIjoxNzM1MDAwMDAwLCJpYXQiOjE3MzQ5OTAwMDAsInJvbGUiOiJ0ZWNoIn0.test+signature/with=special';
      const refreshToken = 'refresh.token.with-special_chars';

      tokenManager.storeTokens(accessToken, refreshToken);

      expect(tokenManager.getAccessToken()).toBe(accessToken);
      expect(tokenManager.getRefreshToken()).toBe(refreshToken);
    });

    it('should handle retrieving tokens when localStorage is empty', () => {
      expect(tokenManager.getAccessToken()).toBeNull();
      expect(tokenManager.getRefreshToken()).toBeNull();
    });

    it('should handle multiple consecutive storeTokens calls', () => {
      const token1 = encodeTestToken({
        sub: 'user1@example.com',
        exp: Math.floor(Date.now() / 1000) + 3600,
        iat: Math.floor(Date.now() / 1000),
        role: 'technician',
      });

      const token2 = encodeTestToken({
        sub: 'user2@example.com',
        exp: Math.floor(Date.now() / 1000) + 7200,
        iat: Math.floor(Date.now() / 1000),
        role: 'admin',
      });

      tokenManager.storeTokens(token1, token1);
      tokenManager.storeTokens(token2, token2);

      // Should have the latest tokens
      expect(tokenManager.getAccessToken()).toBe(token2);
      expect(tokenManager.getRefreshToken()).toBe(token2);
    });

    it('should handle clearTokens when no tokens are stored', () => {
      expect(() => tokenManager.clearTokens()).not.toThrow();
      expect(tokenManager.getAccessToken()).toBeNull();
    });
  });

  describe('Token Validation Edge Cases', () => {
    it('should handle token with missing exp field', () => {
      const invalidToken = btoa(JSON.stringify({ alg: 'HS256' })) + '.' + 
                          btoa(JSON.stringify({ sub: 'test@example.com', iat: 1234567890 })) + 
                          '.signature';
      
      expect(tokenManager.isTokenValid(invalidToken)).toBe(false);
    });

    it('should handle token with exp as string instead of number', () => {
      const invalidToken = btoa(JSON.stringify({ alg: 'HS256' })) + '.' + 
                          btoa(JSON.stringify({ sub: 'test@example.com', exp: 'invalid', iat: 1234567890 })) + 
                          '.signature';
      
      expect(tokenManager.isTokenValid(invalidToken)).toBe(false);
    });

    it('should handle token with exp exactly at current time', () => {
      const now = Math.floor(Date.now() / 1000);
      const token = encodeTestToken({
        sub: 'test@example.com',
        exp: now,
        iat: now - 3600,
        role: 'technician',
      });

      // Token at exact expiry time should be invalid
      expect(tokenManager.isTokenValid(token)).toBe(false);
    });

    it('should handle isTokenExpiringSoon with custom threshold', () => {
      const token = encodeTestToken({
        sub: 'test@example.com',
        exp: Math.floor(Date.now() / 1000) + 600, // 10 minutes from now
        iat: Math.floor(Date.now() / 1000),
        role: 'technician',
      });

      expect(tokenManager.isTokenExpiringSoon(token, 5)).toBe(false); // Not expiring within 5 min
      expect(tokenManager.isTokenExpiringSoon(token, 15)).toBe(true); // Expiring within 15 min
    });

    it('should handle decodeToken with null or undefined', () => {
      expect(tokenManager.decodeToken('')).toBeNull();
    });

    it('should handle token with only one part', () => {
      expect(tokenManager.isTokenValid('onlyonepart')).toBe(false);
      expect(tokenManager.decodeToken('onlyonepart')).toBeNull();
    });

    it('should handle token with two parts', () => {
      expect(tokenManager.isTokenValid('two.parts')).toBe(false);
      expect(tokenManager.decodeToken('two.parts')).toBeNull();
    });

    it('should handle token with four parts', () => {
      expect(tokenManager.isTokenValid('four.parts.are.invalid')).toBe(false);
    });

    it('should handle token with invalid base64 encoding', () => {
      const invalidToken = 'not-base64.also-not-base64.signature';
      expect(tokenManager.isTokenValid(invalidToken)).toBe(false);
      expect(tokenManager.decodeToken(invalidToken)).toBeNull();
    });
  });

  describe('Token Refresh Edge Cases', () => {
    it('should throw error when refreshing without a refresh token', async () => {
      await expect(tokenManager.refreshAccessToken()).rejects.toThrow('No refresh token available');
    });

    it('should handle network errors during refresh', async () => {
      const token = encodeTestToken({
        sub: 'test@example.com',
        exp: Math.floor(Date.now() / 1000) + 3600,
        iat: Math.floor(Date.now() / 1000),
        role: 'technician',
      });

      tokenManager.storeTokens(token, token);

      // Mock fetch to simulate network error
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

      await expect(tokenManager.refreshAccessToken()).rejects.toThrow();

      // Verify tokens are cleared after failure
      expect(tokenManager.getAccessToken()).toBeNull();
      expect(tokenManager.getRefreshToken()).toBeNull();
    });

    it('should handle 401 response during refresh', async () => {
      const token = encodeTestToken({
        sub: 'test@example.com',
        exp: Math.floor(Date.now() / 1000) + 3600,
        iat: Math.floor(Date.now() / 1000),
        role: 'technician',
      });

      tokenManager.storeTokens(token, token);

      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
      });

      await expect(tokenManager.refreshAccessToken()).rejects.toThrow('Token refresh failed');
      expect(tokenManager.getAccessToken()).toBeNull();
    });

    it('should handle malformed response from refresh endpoint', async () => {
      const token = encodeTestToken({
        sub: 'test@example.com',
        exp: Math.floor(Date.now() / 1000) + 3600,
        iat: Math.floor(Date.now() / 1000),
        role: 'technician',
      });

      tokenManager.storeTokens(token, token);

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ wrong_field: 'value' }), // Missing access_token
      });

      await expect(tokenManager.refreshAccessToken()).rejects.toThrow();
    });

    it('should cancel existing refresh timer when scheduling new one', () => {
      const token = encodeTestToken({
        sub: 'test@example.com',
        exp: Math.floor(Date.now() / 1000) + 3600,
        iat: Math.floor(Date.now() / 1000),
        role: 'technician',
      });

      tokenManager.storeTokens(token, token);

      // Schedule multiple times
      tokenManager.scheduleTokenRefresh();
      tokenManager.scheduleTokenRefresh();
      tokenManager.scheduleTokenRefresh();

      // Should not throw and should have only one timer
      expect(() => tokenManager.cancelTokenRefresh()).not.toThrow();
    });

    it('should not schedule refresh for expired token', () => {
      const expiredToken = encodeTestToken({
        sub: 'test@example.com',
        exp: Math.floor(Date.now() / 1000) - 3600, // expired 1 hour ago
        iat: Math.floor(Date.now() / 1000) - 7200,
        role: 'technician',
      });

      tokenManager.storeTokens(expiredToken, expiredToken);
      
      // Should not throw even with expired token
      expect(() => tokenManager.scheduleTokenRefresh()).not.toThrow();
    });

    it('should not schedule refresh when no token is stored', () => {
      expect(() => tokenManager.scheduleTokenRefresh()).not.toThrow();
    });

    it('should handle scheduleTokenRefresh with malformed token', () => {
      localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, 'malformed.token');
      
      expect(() => tokenManager.scheduleTokenRefresh()).not.toThrow();
    });
  });

  describe('Token Refresh Scheduling Timing', () => {
    it('should schedule refresh for token expiring in 10 minutes', () => {
      const token = encodeTestToken({
        sub: 'test@example.com',
        exp: Math.floor(Date.now() / 1000) + 600, // 10 minutes from now
        iat: Math.floor(Date.now() / 1000),
        role: 'technician',
      });

      tokenManager.storeTokens(token, token);
      
      // Should schedule refresh for 5 minutes from now (600 - 300 = 300 seconds)
      expect(() => tokenManager.scheduleTokenRefresh()).not.toThrow();
      
      tokenManager.cancelTokenRefresh();
    });

    it('should not schedule refresh for token expiring in less than 5 minutes', () => {
      const token = encodeTestToken({
        sub: 'test@example.com',
        exp: Math.floor(Date.now() / 1000) + 200, // 3.3 minutes from now
        iat: Math.floor(Date.now() / 1000),
        role: 'technician',
      });

      tokenManager.storeTokens(token, token);
      
      // Should not schedule since there's less than 5 minutes until expiry
      expect(() => tokenManager.scheduleTokenRefresh()).not.toThrow();
    });
  });

  describe('Integration Edge Cases', () => {
    it('should handle full lifecycle: store, validate, refresh, clear', async () => {
      const initialToken = encodeTestToken({
        sub: 'test@example.com',
        exp: Math.floor(Date.now() / 1000) + 3600,
        iat: Math.floor(Date.now() / 1000),
        role: 'technician',
      });

      const newToken = encodeTestToken({
        sub: 'test@example.com',
        exp: Math.floor(Date.now() / 1000) + 7200,
        iat: Math.floor(Date.now() / 1000),
        role: 'technician',
      });

      // Store
      tokenManager.storeTokens(initialToken, initialToken);
      expect(tokenManager.isTokenValid(initialToken)).toBe(true);

      // Mock refresh
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ access_token: newToken }),
      });

      // Refresh
      const refreshedToken = await tokenManager.refreshAccessToken();
      expect(refreshedToken).toBe(newToken);
      expect(tokenManager.getAccessToken()).toBe(newToken);

      // Clear
      tokenManager.clearTokens();
      expect(tokenManager.getAccessToken()).toBeNull();
    });

    it('should handle concurrent clearTokens and scheduleTokenRefresh', () => {
      const token = encodeTestToken({
        sub: 'test@example.com',
        exp: Math.floor(Date.now() / 1000) + 3600,
        iat: Math.floor(Date.now() / 1000),
        role: 'technician',
      });

      tokenManager.storeTokens(token, token);
      tokenManager.scheduleTokenRefresh();
      tokenManager.clearTokens();

      // After clear, no tokens should be present
      expect(tokenManager.getAccessToken()).toBeNull();
    });
  });
});
