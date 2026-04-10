/**
 * API Client Service
 * Axios-based HTTP client with interceptors for authentication and error handling
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosError } from 'axios';
import { APIClient, RequestConfig, RequestCache } from './types';
import { tokenManager } from './tokenManager';

class APIClientImpl implements APIClient {
  private client: AxiosInstance;
  private cache: Map<string, RequestCache> = new Map();
  private readonly CACHE_TTL = 5 * 60 * 1000; // 5 minutes

  constructor() {
    this.client = axios.create({
      baseURL: '/api/v1',
      timeout: 30000,
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  // Expose client for testing
  getAxiosInstance(): AxiosInstance {
    return this.client;
  }

  private setupInterceptors(): void {
    // Request interceptor - add auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = tokenManager.getAccessToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor - handle errors
    this.client.interceptors.response.use(
      (response) => {
        // Cache GET responses
        if (response.config.method === 'get') {
          const cacheKey = this.getCacheKey(
            response.config.url || '',
            response.config.params
          );
          this.cache.set(cacheKey, {
            data: response.data,
            timestamp: Date.now(),
            expiresIn: this.CACHE_TTL,
          });
        }
        return response;
      },
      async (error: AxiosError) => {
        const originalRequest = error.config;

        // Handle network errors (backend not running)
        if (!error.response) {
          console.error('Network error - backend may not be running:', error.message);
          return Promise.reject(error);
        }

        // Handle 401 - Token refresh (but don't redirect immediately)
        if (error.response?.status === 401 && originalRequest && !(originalRequest as any)._retry) {
          (originalRequest as any)._retry = true;

          try {
            const newToken = await tokenManager.refreshAccessToken();
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            return this.client.request(originalRequest);
          } catch (refreshError) {
            // Token refresh failed - only redirect if we're not already on login page
            if (!window.location.pathname.includes('/login')) {
              tokenManager.clearTokens();
              window.location.href = '/login?reason=session_expired';
            }
            return Promise.reject(refreshError);
          }
        }

        // Handle 403 - Permission error
        if (error.response?.status === 403) {
          console.error('Permission denied:', error);
        }

        // Handle 404 - Not found
        if (error.response?.status === 404) {
          console.error('Resource not found:', error);
        }

        // Handle 500 - Server error
        if (error.response?.status === 500) {
          console.error('Server error:', error);
        }

        return Promise.reject(error);
      }
    );
  }

  // HTTP methods
  async get<T>(url: string, config?: RequestConfig): Promise<T> {
    // Check cache first
    if (config?.cache !== false) {
      const cacheKey = this.getCacheKey(url, config?.params);
      const cached = this.cache.get(cacheKey);
      
      if (cached && Date.now() - cached.timestamp < cached.expiresIn) {
        return cached.data as T;
      }
    }

    const response = await this.client.get<T>(url, config as AxiosRequestConfig);
    return response.data;
  }

  async post<T>(url: string, data?: any, config?: RequestConfig): Promise<T> {
    const response = await this.client.post<T>(url, data, config as AxiosRequestConfig);
    return response.data;
  }

  async put<T>(url: string, data?: any, config?: RequestConfig): Promise<T> {
    const response = await this.client.put<T>(url, data, config as AxiosRequestConfig);
    return response.data;
  }

  async delete<T>(url: string, config?: RequestConfig): Promise<T> {
    const response = await this.client.delete<T>(url, config as AxiosRequestConfig);
    return response.data;
  }

  // Configuration
  setBaseURL(url: string): void {
    this.client.defaults.baseURL = url;
  }

  setTimeout(ms: number): void {
    this.client.defaults.timeout = ms;
  }

  // Cache management
  clearCache(): void {
    this.cache.clear();
  }

  getCacheKey(url: string, params?: any): string {
    const paramString = params ? JSON.stringify(params) : '';
    return `${url}${paramString}`;
  }
}

// Export singleton instance
export const apiClient = new APIClientImpl();
