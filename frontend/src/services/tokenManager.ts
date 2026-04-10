/**
 * Token Manager Service
 * Handles JWT token storage, validation, and refresh operations
 */

import { jwtDecode } from 'jwt-decode';
import { TokenManager, TokenPayload, STORAGE_KEYS } from './types';

class TokenManagerImpl implements TokenManager {
  private refreshTimer: NodeJS.Timeout | null = null;

  // Token storage
  storeTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, accessToken);
    localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refreshToken);
    
    const payload = this.decodeToken(accessToken);
    if (payload) {
      localStorage.setItem(STORAGE_KEYS.TOKEN_EXPIRY, payload.exp.toString());
    }
  }

  getAccessToken(): string | null {
    return localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
  }

  getRefreshToken(): string | null {
    return localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
  }

  clearTokens(): void {
    localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
    localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
    localStorage.removeItem(STORAGE_KEYS.TOKEN_EXPIRY);
    localStorage.removeItem(STORAGE_KEYS.USER_DATA);
    this.cancelTokenRefresh();
  }

  // Token validation
  isTokenValid(token: string): boolean {
    try {
      const payload = this.decodeToken(token);
      if (!payload) return false;
      
      const now = Date.now() / 1000;
      return payload.exp > now;
    } catch {
      return false;
    }
  }

  isTokenExpiringSoon(token: string, thresholdMinutes: number = 5): boolean {
    try {
      const payload = this.decodeToken(token);
      if (!payload) return false;
      
      const now = Date.now() / 1000;
      const threshold = thresholdMinutes * 60;
      return payload.exp - now < threshold;
    } catch {
      return false;
    }
  }

  decodeToken(token: string): TokenPayload | null {
    try {
      return jwtDecode<TokenPayload>(token);
    } catch {
      return null;
    }
  }

  // Token refresh
  async refreshAccessToken(): Promise<string> {
    const refreshToken = this.getRefreshToken();
    
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    try {
      // Call the refresh endpoint
      const response = await fetch('/api/v1/auth/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) {
        throw new Error('Token refresh failed');
      }

      const data = await response.json();
      const newAccessToken = data.access_token;

      if (!newAccessToken) {
        throw new Error('Invalid refresh response: missing access_token');
      }

      // Update only the access token in storage
      localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, newAccessToken);
      
      const payload = this.decodeToken(newAccessToken);
      if (payload) {
        localStorage.setItem(STORAGE_KEYS.TOKEN_EXPIRY, payload.exp.toString());
      }

      // Reschedule the next refresh
      this.scheduleTokenRefresh();

      return newAccessToken;
    } catch (error) {
      // Clear tokens on refresh failure
      this.clearTokens();
      throw error;
    }
  }

  scheduleTokenRefresh(): void {
    // Cancel any existing timer
    this.cancelTokenRefresh();

    const token = this.getAccessToken();
    if (!token) {
      return;
    }

    const payload = this.decodeToken(token);
    if (!payload) {
      return;
    }

    const now = Date.now() / 1000;
    const expiresIn = payload.exp - now;
    
    // Schedule refresh 5 minutes (300 seconds) before expiration
    const refreshIn = expiresIn - 300;

    // Only schedule if there's time before expiration
    if (refreshIn > 0) {
      this.refreshTimer = setTimeout(() => {
        this.refreshAccessToken().catch((error) => {
          console.error('Automatic token refresh failed:', error);
        });
      }, refreshIn * 1000);
    }
  }

  cancelTokenRefresh(): void {
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
      this.refreshTimer = null;
    }
  }
}

// Export singleton instance
export const tokenManager = new TokenManagerImpl();
