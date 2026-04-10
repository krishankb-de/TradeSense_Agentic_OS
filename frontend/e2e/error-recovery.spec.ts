/**
 * E2E Test: Error Recovery
 * 
 * Tests error handling and recovery mechanisms including:
 * - Network error handling and retry
 * - 401 error with automatic token refresh
 * - Backend unavailable scenario
 * 
 * Requirements: 2.1, 2.2, 3.1, 3.2, 3.3, 3.4, 11.3
 */

import { test, expect, Page } from '@playwright/test';

// Test credentials
const TEST_USER = {
  email: 'test@test.com',
  password: 'testpass123',
};

// Helper function to perform login
async function login(page: Page, email: string, password: string) {
  await page.goto('/login');
  await page.fill('input[name="email"]', email);
  await page.fill('input[name="password"]', password);
  await page.locator('input[name="password"]').press('Enter');
  await page.waitForURL('/', { timeout: 10000 });
}

test.describe('Error Recovery', () => {
  test.beforeEach(async ({ page }) => {
    // Clear storage before each test
    await page.goto('/login');
    await page.evaluate(() => localStorage.clear());
    await page.context().clearCookies();
  });

  test('should handle network errors gracefully', async ({ page, context }) => {
    // Step 1: Login first
    await login(page, TEST_USER.email, TEST_USER.password);
    await page.waitForURL('/');

    // Step 2: Simulate network failure by going offline
    await context.setOffline(true);

    // Step 3: Try to navigate to a page that requires API call
    await page.goto('/leads');

    // Step 4: Wait for error handling
    await page.waitForTimeout(2000);

    // Step 5: Go back online
    await context.setOffline(false);

    // Step 6: Verify user token still exists (not logged out due to network error)
    const token = await page.evaluate(() => localStorage.getItem('token'));
    expect(token).toBeTruthy();
  });

  test('should handle 401 error with token refresh attempt', async ({ page }) => {
    // Step 1: Login first
    await login(page, TEST_USER.email, TEST_USER.password);
    await page.waitForURL('/');

    // Step 2: Set an expired token to trigger 401
    await page.evaluate(() => {
      const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
      const payload = btoa(JSON.stringify({
        sub: 'test@test.com',
        exp: Math.floor(Date.now() / 1000) - 3600, // Expired 1 hour ago
        iat: Math.floor(Date.now() / 1000) - 7200,
        role: 'admin'
      }));
      const signature = 'fake-signature';
      const expiredToken = `${header}.${payload}.${signature}`;
      localStorage.setItem('token', expiredToken);
    });

    // Step 3: Try to navigate to a protected page
    await page.goto('/leads');

    // Step 4: Wait for token refresh attempt and potential redirect
    await page.waitForTimeout(3000);

    // Step 5: Should be redirected to login (expired token, refresh will fail)
    await page.waitForURL('/login', { timeout: 5000 });
    await expect(page).toHaveURL('/login');

    // Step 6: Verify expired token was cleared
    const token = await page.evaluate(() => localStorage.getItem('token'));
    expect(token).toBeNull();
  });

  test('should handle backend unavailable (503) scenario', async ({ page }) => {
    // Step 1: Intercept login request - simulate backend unavailable
    await page.route('**/api/**', (route) => {
      if (route.request().url().includes('/auth/login')) {
        route.fulfill({
          status: 503,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Service Unavailable' }),
        });
      } else {
        route.continue();
      }
    });

    // Step 2: Navigate to login page
    await page.goto('/login');

    // Step 3: Try to login
    await page.fill('input[name="email"]', TEST_USER.email);
    await page.fill('input[name="password"]', TEST_USER.password);
    await page.click('button[type="submit"]');

    // Step 4: Wait for error handling
    await page.waitForTimeout(2000);

    // Step 5: Verify user is still on login page
    await expect(page).toHaveURL('/login');

    // Step 6: Verify no token was stored
    const token = await page.evaluate(() => localStorage.getItem('token'));
    expect(token).toBeNull();
  });

  test('should handle 500 server error without logging out', async ({ page }) => {
    // Step 1: Login first
    await login(page, TEST_USER.email, TEST_USER.password);
    await page.waitForURL('/');

    // Get the token before error
    const tokenBefore = await page.evaluate(() => localStorage.getItem('token'));
    expect(tokenBefore).toBeTruthy();

    // Step 2: Intercept API requests to return 500 error
    await page.route('**/api/v1/leads**', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal Server Error' }),
      });
    });

    // Step 3: Navigate to leads page
    await page.goto('/leads');

    // Step 4: Wait for error handling
    await page.waitForTimeout(2000);

    // Step 5: Verify user remains authenticated (500 error shouldn't log out)
    const tokenAfter = await page.evaluate(() => localStorage.getItem('token'));
    expect(tokenAfter).toBe(tokenBefore);

    // Step 6: Verify user is still on leads page (not redirected to login)
    await expect(page).toHaveURL('/leads');
  });

  test('should handle 403 permission error without logging out', async ({ page }) => {
    // Step 1: Login first
    await login(page, TEST_USER.email, TEST_USER.password);
    await page.waitForURL('/');

    // Get the token before error
    const tokenBefore = await page.evaluate(() => localStorage.getItem('token'));
    expect(tokenBefore).toBeTruthy();

    // Step 2: Intercept API requests to return 403 error
    await page.route('**/api/v1/technicians**', (route) => {
      route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Forbidden' }),
      });
    });

    // Step 3: Navigate to technicians page
    await page.goto('/technicians');

    // Step 4: Wait for error handling
    await page.waitForTimeout(2000);

    // Step 5: Verify user remains authenticated (403 error shouldn't log out)
    const tokenAfter = await page.evaluate(() => localStorage.getItem('token'));
    expect(tokenAfter).toBe(tokenBefore);

    // Step 6: Verify user is still on technicians page (not redirected to login)
    await expect(page).toHaveURL('/technicians');
  });

  test('should handle 404 not found error without logging out', async ({ page }) => {
    // Step 1: Login first
    await login(page, TEST_USER.email, TEST_USER.password);
    await page.waitForURL('/');

    // Get the token before error
    const tokenBefore = await page.evaluate(() => localStorage.getItem('token'));
    expect(tokenBefore).toBeTruthy();

    // Step 2: Intercept API requests to return 404 error
    await page.route('**/api/v1/leads/999**', (route) => {
      route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Not Found' }),
      });
    });

    // Step 3: Try to fetch a non-existent resource
    await page.evaluate(() => {
      fetch('/api/v1/leads/999', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      }).catch(() => {});
    });

    // Step 4: Wait for error handling
    await page.waitForTimeout(2000);

    // Step 5: Verify user remains authenticated
    const tokenAfter = await page.evaluate(() => localStorage.getItem('token'));
    expect(tokenAfter).toBe(tokenBefore);

    // Step 6: Verify user is not redirected to login
    await expect(page).not.toHaveURL('/login');
  });

  test('should maintain session across page refresh', async ({ page }) => {
    // Step 1: Login
    await login(page, TEST_USER.email, TEST_USER.password);
    await page.waitForURL('/');

    // Step 2: Get token
    const tokenBefore = await page.evaluate(() => localStorage.getItem('token'));
    expect(tokenBefore).toBeTruthy();

    // Step 3: Refresh page
    await page.reload();

    // Step 4: Wait for page to load
    await page.waitForTimeout(2000);

    // Step 5: Verify still authenticated
    const tokenAfter = await page.evaluate(() => localStorage.getItem('token'));
    expect(tokenAfter).toBe(tokenBefore);

    // Step 6: Verify still on dashboard (not redirected to login)
    await expect(page).toHaveURL('/');
  });

  test('should clear session on logout', async ({ page }) => {
    // Step 1: Login
    await login(page, TEST_USER.email, TEST_USER.password);
    await page.waitForURL('/');

    // Step 2: Verify token exists
    const tokenBefore = await page.evaluate(() => localStorage.getItem('token'));
    expect(tokenBefore).toBeTruthy();

    // Step 3: Logout
    const userProfileButton = page.locator('[data-testid="user-profile"] button').first();
    await userProfileButton.click();
    await page.waitForTimeout(500);
    
    const logoutButton = page.locator('button:has-text("Logout")');
    await logoutButton.click();

    // Step 4: Wait for redirect
    await page.waitForURL('/login', { timeout: 5000 });

    // Step 5: Verify token was cleared
    const tokenAfter = await page.evaluate(() => localStorage.getItem('token'));
    expect(tokenAfter).toBeNull();

    // Step 6: Verify on login page
    await expect(page).toHaveURL('/login');
  });

  test('should handle multiple API errors without breaking', async ({ page }) => {
    // Step 1: Login first
    await login(page, TEST_USER.email, TEST_USER.password);
    await page.waitForURL('/');

    // Step 2: Intercept multiple API endpoints with different errors
    await page.route('**/api/v1/leads**', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Server Error' }),
      });
    });

    await page.route('**/api/v1/jobs**', (route) => {
      route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Forbidden' }),
      });
    });

    // Step 3: Navigate to dashboard (which might call multiple APIs)
    await page.goto('/');

    // Step 4: Wait for error handling
    await page.waitForTimeout(2000);

    // Step 5: Verify user remains authenticated
    const token = await page.evaluate(() => localStorage.getItem('token'));
    expect(token).toBeTruthy();

    // Step 6: Verify user is not redirected to login
    await expect(page).toHaveURL('/');
  });

  test('should handle connection timeout gracefully', async ({ page, context }) => {
    // Step 1: Login first
    await login(page, TEST_USER.email, TEST_USER.password);
    await page.waitForURL('/');

    // Step 2: Slow down network to simulate timeout
    await context.route('**/api/v1/leads**', async (route) => {
      // Delay response significantly
      await new Promise(resolve => setTimeout(resolve, 5000));
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    // Step 3: Navigate to leads page
    await page.goto('/leads');

    // Step 4: Wait for timeout handling
    await page.waitForTimeout(6000);

    // Step 5: Verify user remains authenticated
    const token = await page.evaluate(() => localStorage.getItem('token'));
    expect(token).toBeTruthy();

    // Step 6: Verify user is not redirected to login
    await expect(page).toHaveURL('/leads');
  });
});
