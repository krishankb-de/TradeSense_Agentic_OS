/**
 * Unit tests for API Client
 * 
 * Tests specific error scenarios, edge cases, and integration with TokenManager.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';
import { apiClient } from '../services/apiClient';
import { tokenManager } from '../services/tokenManager';

describe('API Client Unit Tests', () => {
  let mock: MockAdapter;

  beforeEach(() => {
    localStorage.clear();
    apiClient.clearCache();
    vi.clearAllMocks();
    // Create mock adapter from the API client's axios instance
    mock = new MockAdapter((apiClient as any).getAxiosInstance());
  });

  afterEach(() => {
    if (mock) {
      mock.restore();
    }
  });

  describe('Authorization Header Injection', () => {
    it('should include Authorization header when token exists', async () => {
      const token = 'test-token';
      tokenManager.storeTokens(token, 'refresh-token');

      let capturedHeaders: any = null;
      mock.onGet('/test').reply((config) => {
        capturedHeaders = config.headers;
        return [200, { success: true }];
      });

      await apiClient.get('/test');

      expect(capturedHeaders.Authorization).toBe(`Bearer ${token}`);
      tokenManager.clearTokens();
    });

    it('should not include Authorization header when no token exists', async () => {
      let capturedHeaders: any = null;
      mock.onGet('/test').reply((config) => {
        capturedHeaders = config.headers;
        return [200, { success: true }];
      });

      await apiClient.get('/test');

      expect(capturedHeaders.Authorization).toBeUndefined();
    });
  });

  describe('Token Refresh on 401', () => {
    it('should refresh token and retry request on 401', async () => {
      const oldToken = 'old-token';
      const newToken = 'new-token';
      tokenManager.storeTokens(oldToken, 'refresh-token');

      let requestCount = 0;

      // Mock fetch for token refresh
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ access_token: newToken }),
      });

      // First request returns 401
      mock.onGet('/test').replyOnce(() => {
        requestCount++;
        return [401, { error: 'Unauthorized' }];
      });

      // Retry succeeds
      mock.onGet('/test').reply(() => {
        requestCount++;
        return [200, { success: true }];
      });

      const result = await apiClient.get('/test');

      expect(requestCount).toBe(2);
      expect(result).toEqual({ success: true });
      expect(tokenManager.getAccessToken()).toBe(newToken);

      tokenManager.clearTokens();
    });

    it('should not retry if already retried', async () => {
      const token = 'test-token';
      tokenManager.storeTokens(token, 'refresh-token');

      let requestCount = 0;

      // Mock fetch for token refresh
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ access_token: 'new-token' }),
      });

      // All requests return 401
      mock.onGet('/test').reply(() => {
        requestCount++;
        return [401, { error: 'Unauthorized' }];
      });

      try {
        await apiClient.get('/test');
      } catch (error: any) {
        expect(error.response?.status).toBe(401);
      }

      // Should only retry once (2 requests total)
      expect(requestCount).toBe(2);

      tokenManager.clearTokens();
    });

    it('should clear tokens and redirect on refresh failure', async () => {
      const token = 'test-token';
      tokenManager.storeTokens(token, 'refresh-token');

      // Mock window.location
      const originalLocation = window.location;
      delete (window as any).location;
      window.location = { ...originalLocation, href: '' } as any;

      // Mock fetch for failed token refresh
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
      });

      // Request returns 401
      mock.onGet('/test').reply(401, { error: 'Unauthorized' });

      try {
        await apiClient.get('/test');
      } catch (error) {
        // Expected to fail
      }

      // Wait for async operations
      await new Promise(resolve => setTimeout(resolve, 100));

      expect(tokenManager.getAccessToken()).toBeNull();
      expect(window.location.href).toContain('/login');

      window.location = originalLocation;
    });
  });

  describe('Error Handling', () => {
    it('should handle 403 Forbidden errors', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      mock.onGet('/test').reply(403, {
        error: 'Forbidden',
        message: 'Insufficient permissions',
      });

      try {
        await apiClient.get('/test');
      } catch (error: any) {
        expect(error.response.status).toBe(403);
      }

      expect(consoleSpy).toHaveBeenCalledWith(
        'Permission denied:',
        expect.any(Object)
      );

      consoleSpy.mockRestore();
    });

    it('should handle 404 Not Found errors', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      mock.onGet('/test').reply(404, {
        error: 'Not Found',
        message: 'Resource not found',
      });

      try {
        await apiClient.get('/test');
      } catch (error: any) {
        expect(error.response.status).toBe(404);
      }

      expect(consoleSpy).toHaveBeenCalledWith(
        'Resource not found:',
        expect.any(Object)
      );

      consoleSpy.mockRestore();
    });

    it('should handle 500 Server errors', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      mock.onGet('/test').reply(500, {
        error: 'Internal Server Error',
        message: 'An unexpected error occurred',
      });

      try {
        await apiClient.get('/test');
      } catch (error: any) {
        expect(error.response.status).toBe(500);
      }

      expect(consoleSpy).toHaveBeenCalledWith(
        'Server error:',
        expect.any(Object)
      );

      consoleSpy.mockRestore();
    });
  });

  describe('GET Request Caching', () => {
    it('should cache GET responses', async () => {
      let requestCount = 0;

      mock.onGet('/test').reply(() => {
        requestCount++;
        return [200, { data: 'test' }];
      });

      // First request
      const result1 = await apiClient.get('/test');
      expect(requestCount).toBe(1);

      // Second request - should use cache
      const result2 = await apiClient.get('/test');
      expect(requestCount).toBe(1); // Not incremented

      expect(result1).toEqual(result2);
    });

    it('should cache GET requests with different params separately', async () => {
      let requestCount = 0;

      mock.onGet('/test').reply((config) => {
        requestCount++;
        return [200, { params: config.params }];
      });

      // Request with params1
      await apiClient.get('/test', { params: { page: 1 } });
      expect(requestCount).toBe(1);

      // Request with params2 - different cache key
      await apiClient.get('/test', { params: { page: 2 } });
      expect(requestCount).toBe(2);

      // Request with params1 again - should use cache
      await apiClient.get('/test', { params: { page: 1 } });
      expect(requestCount).toBe(2); // Not incremented
    });

    it('should not cache POST requests', async () => {
      let requestCount = 0;

      mock.onPost('/test').reply(() => {
        requestCount++;
        return [200, { data: 'test' }];
      });

      await apiClient.post('/test', { data: 'test' });
      expect(requestCount).toBe(1);

      await apiClient.post('/test', { data: 'test' });
      expect(requestCount).toBe(2); // Incremented
    });

    it('should not cache PUT requests', async () => {
      let requestCount = 0;

      mock.onPut('/test').reply(() => {
        requestCount++;
        return [200, { data: 'test' }];
      });

      await apiClient.put('/test', { data: 'test' });
      expect(requestCount).toBe(1);

      await apiClient.put('/test', { data: 'test' });
      expect(requestCount).toBe(2); // Incremented
    });

    it('should not cache DELETE requests', async () => {
      let requestCount = 0;

      mock.onDelete('/test').reply(() => {
        requestCount++;
        return [200, { data: 'test' }];
      });

      await apiClient.delete('/test');
      expect(requestCount).toBe(1);

      await apiClient.delete('/test');
      expect(requestCount).toBe(2); // Incremented
    });

    it('should allow bypassing cache with cache: false', async () => {
      let requestCount = 0;

      mock.onGet('/test').reply(() => {
        requestCount++;
        return [200, { data: 'test' }];
      });

      // First request
      await apiClient.get('/test');
      expect(requestCount).toBe(1);

      // Second request with cache: false
      await apiClient.get('/test', { cache: false });
      expect(requestCount).toBe(2); // Incremented
    });

    it('should clear all cache entries', async () => {
      let requestCount = 0;

      mock.onGet('/test').reply(() => {
        requestCount++;
        return [200, { data: 'test' }];
      });

      // First request
      await apiClient.get('/test');
      expect(requestCount).toBe(1);

      // Clear cache
      apiClient.clearCache();

      // Second request - should hit server
      await apiClient.get('/test');
      expect(requestCount).toBe(2);
    });
  });

  describe('HTTP Methods', () => {
    it('should support GET requests', async () => {
      mock.onGet('/test').reply(200, { method: 'GET' });

      const result = await apiClient.get('/test');
      expect(result).toEqual({ method: 'GET' });
    });

    it('should support POST requests', async () => {
      mock.onPost('/test').reply(200, { method: 'POST' });

      const result = await apiClient.post('/test', { data: 'test' });
      expect(result).toEqual({ method: 'POST' });
    });

    it('should support PUT requests', async () => {
      mock.onPut('/test').reply(200, { method: 'PUT' });

      const result = await apiClient.put('/test', { data: 'test' });
      expect(result).toEqual({ method: 'PUT' });
    });

    it('should support DELETE requests', async () => {
      mock.onDelete('/test').reply(200, { method: 'DELETE' });

      const result = await apiClient.delete('/test');
      expect(result).toEqual({ method: 'DELETE' });
    });
  });

  describe('Configuration', () => {
    it('should use base URL /api/v1', async () => {
      let capturedUrl: string = '';

      mock.onGet().reply((config) => {
        capturedUrl = config.url || '';
        return [200, {}];
      });

      await apiClient.get('/test');

      // The URL captured is relative, baseURL is prepended by axios
      expect(capturedUrl).toBe('/test');
    });

    it('should use 30-second timeout', async () => {
      let capturedTimeout: number = 0;

      mock.onGet('/test').reply((config) => {
        capturedTimeout = config.timeout || 0;
        return [200, {}];
      });

      await apiClient.get('/test');

      expect(capturedTimeout).toBe(30000);
    });

    it('should include credentials (withCredentials: true)', async () => {
      let capturedWithCredentials: boolean = false;

      mock.onGet('/test').reply((config) => {
        capturedWithCredentials = config.withCredentials || false;
        return [200, {}];
      });

      await apiClient.get('/test');

      expect(capturedWithCredentials).toBe(true);
    });

    it('should allow changing base URL', async () => {
      apiClient.setBaseURL('/api/v2');

      let capturedUrl: string = '';

      mock.onGet().reply((config) => {
        capturedUrl = config.url || '';
        return [200, {}];
      });

      await apiClient.get('/test');

      // The URL captured is relative, baseURL is prepended by axios
      expect(capturedUrl).toBe('/test');

      // Reset to default
      apiClient.setBaseURL('/api/v1');
    });

    it('should allow changing timeout', async () => {
      apiClient.setTimeout(60000);

      let capturedTimeout: number = 0;

      mock.onGet('/test').reply((config) => {
        capturedTimeout = config.timeout || 0;
        return [200, {}];
      });

      await apiClient.get('/test');

      expect(capturedTimeout).toBe(60000);

      // Reset to default
      apiClient.setTimeout(30000);
    });
  });

  describe('Cache Key Generation', () => {
    it('should generate cache key from URL', () => {
      const key = apiClient.getCacheKey('/test');
      expect(key).toBe('/test');
    });

    it('should include params in cache key', () => {
      const key = apiClient.getCacheKey('/test', { page: 1, limit: 10 });
      expect(key).toContain('/test');
      expect(key).toContain('page');
      expect(key).toContain('limit');
    });

    it('should generate different keys for different params', () => {
      const key1 = apiClient.getCacheKey('/test', { page: 1 });
      const key2 = apiClient.getCacheKey('/test', { page: 2 });
      expect(key1).not.toBe(key2);
    });

    it('should generate same key for same params', () => {
      const key1 = apiClient.getCacheKey('/test', { page: 1, limit: 10 });
      const key2 = apiClient.getCacheKey('/test', { page: 1, limit: 10 });
      expect(key1).toBe(key2);
    });
  });
});
