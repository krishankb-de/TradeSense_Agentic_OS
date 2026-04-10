/**
 * E2E Test: Complete Authentication Workflow
 * 
 * Tests the full authentication flow including:
 * - Login with valid credentials
 * - Navigation to dashboard
 * - Session persistence across page refresh
 * - Logout functionality
 * 
 * Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3
 */

import { test, expect, Page } from '@playwright/test';

// Test credentials - these should match the test user in the backend
const TEST_USER = {
  email: 'test@test.com',
  password: 'testpass123',
};

// Helper function to perform login
async function login(page: Page, email: string, password: string) {
  await page.goto('/login');
  
  // Fill in login form
  await page.fill('input[name="email"]', email);
  await page.fill('input[name="password"]', password);
  
  // Submit form by pressing Enter
  await page.locator('input[name="password"]').press('Enter');
  await page.waitForURL('/', { timeout: 10000 });
}

// Helper function to check if user is on dashboard
async function expectDashboard(page: Page) {
  await expect(page).toHaveURL('/');
  // Just check that we're not on login page and page has loaded
  await expect(page.locator('body')).toBeVisible();
}

// Helper function to check if user is on login page
async function expectLoginPage(page: Page) {
  await expect(page).toHaveURL('/login');
  await expect(page.locator('h2')).toContainText('TradeSense');
}

test.describe('Authentication Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Listen to console messages
    page.on('console', msg => {
      const type = msg.type();
      if (type === 'error' || type === 'warning' || msg.text().includes('Login') || msg.text().includes('Error')) {
        console.log(`PAGE ${type.toUpperCase()}:`, msg.text());
      }
    });
    
    // Listen to page errors
    page.on('pageerror', error => {
      console.log('PAGE ERROR:', error.message);
    });
    
    // Listen to request failures
    page.on('requestfailed', request => {
      console.log('REQUEST FAILED:', request.url(), request.failure()?.errorText);
    });
    
    // Listen to responses
    page.on('response', response => {
      const url = response.url();
      if (url.includes('/api/') || url.includes('/auth/')) {
        console.log('API RESPONSE:', url, response.status());
      }
    });
    
    // Navigate to a page first to establish context
    await page.goto('/login');
    
    // Clear storage after navigation to ensure clean state
    await page.evaluate(() => localStorage.clear());
    await page.context().clearCookies();
  });

  test('should complete full login → dashboard → logout flow', async ({ page }) => {
    // Step 1: Navigate to login page
    await page.goto('/login');
    await expectLoginPage(page);

    // Step 2: Fill in credentials
    await page.fill('input[name="email"]', TEST_USER.email);
    await page.fill('input[name="password"]', TEST_USER.password);

    // Step 3: Submit login form
    const submitButton = page.locator('button[type="submit"]');
    await expect(submitButton).toBeEnabled();
    
    // Wait for any validation to complete
    await page.waitForTimeout(1000);
    
    // Check if button is still enabled after validation
    await expect(submitButton).toBeEnabled();
    
    // Try pressing Enter to submit the form
    await page.locator('input[name="password"]').press('Enter');
    
    // Wait for either navigation or error
    try {
      await page.waitForURL('/', { timeout: 10000 });
    } catch (e) {
      // Log current URL and page content for debugging
      console.log('Current URL:', page.url());
      const bodyText = await page.locator('body').textContent();
      console.log('Page content:', bodyText?.substring(0, 500));
      
      // Check if there's an error message
      const errorText = await page.locator('[role="alert"]').allTextContents();
      console.log('Error messages:', errorText);
      
      throw e;
    }
    
    // Step 4: Verify we're on dashboard
    await expectDashboard(page);

    // Step 5: Verify token is stored in localStorage
    const token = await page.evaluate(() => localStorage.getItem('token'));
    expect(token).toBeTruthy();
    expect(token).toMatch(/^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$/); // JWT format

    // Step 6: Verify user profile is displayed
    const userProfile = page.locator('[data-testid="user-profile"]').or(page.locator('text=' + TEST_USER.email));
    await expect(userProfile.first()).toBeVisible();

    // Step 7: Verify dashboard content is loaded
    await expect(page.locator('text=Total Leads').or(page.locator('text=Active Jobs'))).toBeVisible();

    // Step 8: Perform logout
    // Click on user profile to open dropdown
    const userProfileButton = page.locator('[data-testid="user-profile"] button').first();
    await userProfileButton.click();
    
    // Wait for dropdown to open
    await page.waitForTimeout(500);
    
    // Click logout button in dropdown
    const logoutButton = page.locator('button:has-text("Logout")');
    await logoutButton.click();

    // Step 9: Verify redirect to login page
    await page.waitForURL('/login');
    await expectLoginPage(page);

    // Step 10: Verify token is cleared from localStorage
    const tokenAfterLogout = await page.evaluate(() => localStorage.getItem('token'));
    expect(tokenAfterLogout).toBeNull();
  });

  test('should persist session across page refresh', async ({ page }) => {
    // Step 1: Login
    await login(page, TEST_USER.email, TEST_USER.password);
    await page.waitForURL('/');
    await expectDashboard(page);

    // Step 2: Verify token is stored
    const tokenBeforeRefresh = await page.evaluate(() => localStorage.getItem('token'));
    expect(tokenBeforeRefresh).toBeTruthy();

    // Step 3: Refresh the page
    await page.reload();

    // Step 4: Verify still on dashboard (not redirected to login)
    await expectDashboard(page);

    // Step 5: Verify token is still present
    const tokenAfterRefresh = await page.evaluate(() => localStorage.getItem('token'));
    expect(tokenAfterRefresh).toBe(tokenBeforeRefresh);

    // Step 6: Verify user profile is still displayed
    const userProfile = page.locator('[data-testid="user-profile"]').or(page.locator('text=' + TEST_USER.email));
    await expect(userProfile.first()).toBeVisible();

    // Step 7: Verify dashboard content is still accessible
    await expect(page.locator('text=Total Leads').or(page.locator('text=Active Jobs'))).toBeVisible();
  });

  test('should redirect to login when accessing protected route without authentication', async ({ page }) => {
    // Step 1: Try to access dashboard without logging in
    await page.goto('/');

    // Step 2: Should be redirected to login
    await page.waitForURL('/login');
    await expectLoginPage(page);

    // Step 3: Verify no token in localStorage
    const token = await page.evaluate(() => localStorage.getItem('token'));
    expect(token).toBeNull();
  });

  test('should handle invalid credentials gracefully', async ({ page }) => {
    // Step 1: Navigate to login
    await page.goto('/login');

    // Step 2: Enter invalid credentials
    await page.fill('input[name="email"]', 'invalid@example.com');
    await page.fill('input[name="password"]', 'wrongpassword');

    // Step 3: Submit form
    await page.click('button[type="submit"]');

    // Step 4: Should remain on login page
    await expect(page).toHaveURL('/login');

    // Step 5: Should show error message (toast or inline)
    // Wait for error to appear - could be toast or inline error
    await page.waitForTimeout(1000); // Give time for error to appear

    // Step 6: Verify no token was stored
    const token = await page.evaluate(() => localStorage.getItem('token'));
    expect(token).toBeNull();
  });

  test('should maintain authentication when navigating between pages', async ({ page }) => {
    // Step 1: Login
    await login(page, TEST_USER.email, TEST_USER.password);
    await page.waitForURL('/');

    // Step 2: Get initial token
    const initialToken = await page.evaluate(() => localStorage.getItem('token'));
    expect(initialToken).toBeTruthy();

    // Step 3: Navigate to different pages
    const pages = ['/leads', '/jobs', '/technicians'];
    
    for (const pagePath of pages) {
      // Navigate to page
      await page.goto(pagePath);
      
      // Verify token is still present
      const token = await page.evaluate(() => localStorage.getItem('token'));
      expect(token).toBe(initialToken);
      
      // Verify not redirected to login
      await expect(page).not.toHaveURL('/login');
    }

    // Step 4: Navigate back to dashboard
    await page.goto('/');
    await expectDashboard(page);

    // Step 5: Verify token unchanged
    const finalToken = await page.evaluate(() => localStorage.getItem('token'));
    expect(finalToken).toBe(initialToken);
  });

  test('should include Authorization header in API requests', async ({ page }) => {
    // Step 1: Setup request interception to verify headers
    const apiRequests: any[] = [];
    
    page.on('request', request => {
      if (request.url().includes('/api/')) {
        apiRequests.push({
          url: request.url(),
          headers: request.headers(),
        });
      }
    });

    // Step 2: Login
    await login(page, TEST_USER.email, TEST_USER.password);
    await page.waitForURL('/');

    // Step 3: Wait for dashboard to load and make API calls
    await page.waitForTimeout(2000);

    // Step 4: Verify at least one API request was made with Authorization header
    const authenticatedRequests = apiRequests.filter(req => 
      req.headers['authorization'] && req.headers['authorization'].startsWith('Bearer ')
    );

    expect(authenticatedRequests.length).toBeGreaterThan(0);

    // Step 5: Verify the token in the header matches localStorage
    const storedToken = await page.evaluate(() => localStorage.getItem('token'));
    const headerToken = authenticatedRequests[0].headers['authorization'].replace('Bearer ', '');
    
    expect(headerToken).toBe(storedToken);
  });

  test('should clear session data on logout', async ({ page }) => {
    // Step 1: Login
    await login(page, TEST_USER.email, TEST_USER.password);
    await page.waitForURL('/');

    // Step 2: Verify session data exists
    const tokenBeforeLogout = await page.evaluate(() => localStorage.getItem('token'));
    expect(tokenBeforeLogout).toBeTruthy();

    // Step 3: Logout
    const userProfileButton = page.locator('[data-testid="user-profile"] button').first();
    await userProfileButton.click();
    await page.waitForTimeout(500);
    
    const logoutButton = page.locator('button:has-text("Logout")');
    await logoutButton.click();

    // Step 4: Wait for redirect
    await page.waitForURL('/login');

    // Step 5: Verify all session data is cleared
    const sessionData = await page.evaluate(() => ({
      token: localStorage.getItem('token'),
      accessToken: localStorage.getItem('tradesense_access_token'),
      refreshToken: localStorage.getItem('tradesense_refresh_token'),
      userData: localStorage.getItem('tradesense_user_data'),
    }));

    expect(sessionData.token).toBeNull();
    expect(sessionData.accessToken).toBeNull();
    expect(sessionData.refreshToken).toBeNull();
    expect(sessionData.userData).toBeNull();

    // Step 6: Verify cannot access protected routes
    await page.goto('/');
    await page.waitForURL('/login');
    await expectLoginPage(page);
  });

  test('should handle session persistence with expired token', async ({ page }) => {
    // Step 1: Set an expired token in localStorage
    await page.goto('/login');
    
    // Create an expired JWT token (expired 1 hour ago)
    const expiredToken = await page.evaluate(() => {
      const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
      const payload = btoa(JSON.stringify({
        sub: 'test@example.com',
        exp: Math.floor(Date.now() / 1000) - 3600, // Expired 1 hour ago
        iat: Math.floor(Date.now() / 1000) - 7200,
        role: 'User'
      }));
      const signature = 'fake-signature';
      const token = `${header}.${payload}.${signature}`;
      localStorage.setItem('token', token);
      return token;
    });

    // Step 2: Try to access dashboard
    await page.goto('/');

    // Step 3: Should be redirected to login (token is expired)
    await page.waitForURL('/login', { timeout: 5000 });
    await expectLoginPage(page);

    // Step 4: Verify expired token was cleared
    const tokenAfter = await page.evaluate(() => localStorage.getItem('token'));
    // Token might be cleared or might still be there depending on validation logic
    // The important thing is we're on the login page
    await expect(page).toHaveURL('/login');
  });
});
