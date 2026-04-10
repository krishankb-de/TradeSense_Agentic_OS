/**
 * E2E Test: Form Validation and Error Handling
 * 
 * Tests form validation behavior and error handling including:
 * - Empty form submission validation
 * - Email format validation
 * - Password length and complexity validation
 * - Required field validation
 * - Validation feedback display (error icons, messages)
 * - Form submit button enablement based on validation state
 * 
 * Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
 */

import { test, expect } from '@playwright/test';

test.describe('Form Validation and Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    // Clear storage before each test
    await page.goto('/login');
    await page.evaluate(() => localStorage.clear());
    await page.context().clearCookies();
  });

  test('should show validation errors when submitting empty form', async ({ page }) => {
    // Requirement 6.3: Required field validation
    await page.goto('/login');

    const emailInput = page.locator('input[name="email"]');
    const passwordInput = page.locator('input[name="password"]');
    const submitButton = page.locator('button[type="submit"]');

    // Ensure fields are empty
    await emailInput.clear();
    await passwordInput.clear();

    // Click submit with empty fields
    await submitButton.click();

    // Wait for validation errors to appear
    const emailError = page.locator('text=Email is required');
    const passwordError = page.locator('text=Password is required');
    
    await expect(emailError).toBeVisible({ timeout: 10000 });
    await expect(passwordError).toBeVisible({ timeout: 10000 });

    // Verify error icons are displayed (AlertCircle icons)
    const errorIcons = page.locator('[role="alert"] svg');
    await expect(errorIcons).toHaveCount(2);

    // Verify errors are in red text (Requirement 6.4)
    const emailErrorContainer = page.locator('input[name="email"]').locator('..').locator('..').locator('[role="alert"]');
    await expect(emailErrorContainer).toHaveClass(/text-red-600/);

    // Form should remain on login page
    await expect(page).toHaveURL('/login');
  });

  test('should validate email format and show appropriate error message', async ({ page }) => {
    // Requirement 6.1: Email validation
    await page.goto('/login');

    const emailInput = page.locator('input[name="email"]');
    const passwordInput = page.locator('input[name="password"]');

    // Test various invalid email formats
    const invalidEmails = [
      'notanemail',           // No @ symbol
      'missing@domain',       // No TLD
      '@nodomain.com',        // No local part
      'spaces in@email.com',  // Spaces
      'double@@domain.com',   // Double @
    ];

    for (const invalidEmail of invalidEmails) {
      // Enter invalid email
      await emailInput.fill(invalidEmail);
      
      // Enter valid password to isolate email validation
      await passwordInput.fill('ValidPass123');
      
      // Blur email field to trigger validation
      await emailInput.blur();
      
      // Wait for validation to appear
      await page.waitForTimeout(100);

      // Should show email validation error
      const emailError = page.locator('text=Please enter a valid email address');
      await expect(emailError).toBeVisible();

      // Should show error icon (Requirement 6.4)
      const errorIcon = page.locator('input[name="email"]').locator('..').locator('..').locator('[role="alert"] svg').first();
      await expect(errorIcon).toBeVisible();

      // Clear for next iteration
      await emailInput.clear();
    }
  });

  test('should validate password length and show error for short passwords', async ({ page }) => {
    // Requirement 6.2: Password length validation
    await page.goto('/login');

    const emailInput = page.locator('input[name="email"]');
    const passwordInput = page.locator('input[name="password"]');

    // Enter valid email
    await emailInput.fill('test@example.com');
    await emailInput.blur();

    // Test passwords shorter than 8 characters
    const shortPasswords = ['short', '1234567', 'abc', 'Pass1'];

    for (const shortPassword of shortPasswords) {
      // Enter short password
      await passwordInput.fill(shortPassword);
      
      // Blur to trigger validation
      await passwordInput.blur();
      
      // Wait for validation
      await page.waitForTimeout(100);

      // Should show password length error
      const passwordError = page.locator('text=Password must be at least 8 characters');
      await expect(passwordError).toBeVisible();

      // Should show error icon in red (Requirement 6.4)
      const errorIcon = page.locator('input[name="password"]').locator('..').locator('..').locator('[role="alert"] svg').first();
      await expect(errorIcon).toBeVisible();
      
      const errorContainer = page.locator('input[name="password"]').locator('..').locator('..').locator('[role="alert"]');
      await expect(errorContainer).toHaveClass(/text-red-600/);

      // Clear for next iteration
      await passwordInput.clear();
    }
  });

  test('should validate password complexity requirements', async ({ page }) => {
    // Requirement 6.2: Password must contain letter and number
    await page.goto('/login');

    const emailInput = page.locator('input[name="email"]');
    const passwordInput = page.locator('input[name="password"]');

    // Enter valid email
    await emailInput.fill('test@example.com');
    await emailInput.blur();

    // Test passwords without required complexity
    const invalidPasswords = [
      'onlyletters',      // No numbers
      '12345678',         // No letters
      'UPPERCASE',        // No numbers
    ];

    for (const invalidPassword of invalidPasswords) {
      await passwordInput.fill(invalidPassword);
      await passwordInput.blur();
      await page.waitForTimeout(100);

      // Should show complexity error
      const complexityError = page.locator('text=Password must contain at least one letter and one number');
      await expect(complexityError).toBeVisible();

      await passwordInput.clear();
    }
  });

  test('should show validation feedback when fields are blurred', async ({ page }) => {
    // Requirement 6.3: Validation on blur
    await page.goto('/login');

    const emailInput = page.locator('input[name="email"]');
    const passwordInput = page.locator('input[name="password"]');

    // Focus and blur email without entering anything
    await emailInput.focus();
    await emailInput.blur();
    await page.waitForTimeout(200);

    // Should show required error for email
    const emailRequiredError = page.locator('input[name="email"]').locator('..').locator('..').locator('text=Email is required');
    await expect(emailRequiredError).toBeVisible();

    // Focus and blur password without entering anything
    await passwordInput.focus();
    await passwordInput.blur();
    await page.waitForTimeout(200);

    // Should show required error for password
    const passwordRequiredError = page.locator('input[name="password"]').locator('..').locator('..').locator('text=Password is required');
    await expect(passwordRequiredError).toBeVisible();
  });

  test('should show green checkmark for valid inputs', async ({ page }) => {
    // Requirement 6.5: Show successful validation with green checkmark
    await page.goto('/login');

    const emailInput = page.locator('input[name="email"]');
    const passwordInput = page.locator('input[name="password"]');

    // Enter valid email
    await emailInput.fill('valid@example.com');
    await emailInput.blur();
    await page.waitForTimeout(100);

    // Should show green checkmark for valid email
    const emailFeedback = page.locator('input[name="email"]').locator('..').locator('..').locator('[role="alert"]');
    await expect(emailFeedback).toHaveClass(/text-green-600/);
    
    // Should contain CheckCircle icon (green checkmark)
    const emailCheckIcon = emailFeedback.locator('svg').first();
    await expect(emailCheckIcon).toBeVisible();

    // Enter valid password
    await passwordInput.fill('ValidPass123');
    await passwordInput.blur();
    await page.waitForTimeout(100);

    // Should show green checkmark for valid password
    const passwordFeedback = page.locator('input[name="password"]').locator('..').locator('..').locator('[role="alert"]');
    await expect(passwordFeedback).toHaveClass(/text-green-600/);
    
    const passwordCheckIcon = passwordFeedback.locator('svg').first();
    await expect(passwordCheckIcon).toBeVisible();
  });

  test('should update validation state dynamically as user types', async ({ page }) => {
    // Test real-time validation feedback
    await page.goto('/login');

    const emailInput = page.locator('input[name="email"]');
    const passwordInput = page.locator('input[name="password"]');

    // Start with invalid email
    await emailInput.fill('invalid');
    await emailInput.blur();
    await page.waitForTimeout(100);

    // Should show error
    let emailError = page.locator('text=Please enter a valid email address');
    await expect(emailError).toBeVisible();

    // Fix the email
    await emailInput.fill('valid@example.com');
    await emailInput.blur();
    await page.waitForTimeout(100);

    // Error should be replaced with success indicator
    await expect(emailError).not.toBeVisible();
    const emailSuccess = page.locator('input[name="email"]').locator('..').locator('..').locator('[role="alert"]');
    await expect(emailSuccess).toHaveClass(/text-green-600/);

    // Start with short password
    await passwordInput.fill('short');
    await passwordInput.blur();
    await page.waitForTimeout(100);

    // Should show length error
    let passwordError = page.locator('text=Password must be at least 8 characters');
    await expect(passwordError).toBeVisible();

    // Fix the password
    await passwordInput.fill('ValidPass123');
    await passwordInput.blur();
    await page.waitForTimeout(100);

    // Error should be replaced with success indicator
    await expect(passwordError).not.toBeVisible();
    const passwordSuccess = page.locator('input[name="password"]').locator('..').locator('..').locator('[role="alert"]');
    await expect(passwordSuccess).toHaveClass(/text-green-600/);
  });

  test('should prevent form submission when validation fails', async ({ page }) => {
    // Requirement 6.6: Form submit should be prevented when validation fails
    await page.goto('/login');

    const emailInput = page.locator('input[name="email"]');
    const passwordInput = page.locator('input[name="password"]');
    const submitButton = page.locator('button[type="submit"]');

    // Enter invalid data
    await emailInput.fill('invalid-email');
    await passwordInput.fill('short');
    
    // Blur to trigger validation
    await emailInput.blur();
    await passwordInput.blur();
    await page.waitForTimeout(100);

    // Try to submit
    await submitButton.click();

    // Should remain on login page (not navigate away)
    await expect(page).toHaveURL('/login');

    // Validation errors should still be visible
    const emailError = page.locator('text=Please enter a valid email address');
    await expect(emailError).toBeVisible();

    const passwordError = page.locator('text=Password must be at least 8 characters');
    await expect(passwordError).toBeVisible();
  });

  test('should allow form submission when all validations pass', async ({ page }) => {
    // Requirement 6.6: Form submit should be enabled when all fields are valid
    await page.goto('/login');

    const emailInput = page.locator('input[name="email"]');
    const passwordInput = page.locator('input[name="password"]');
    const submitButton = page.locator('button[type="submit"]');

    // Enter valid data
    await emailInput.fill('admin@tradesense.com');
    await passwordInput.fill('admin123');
    
    // Blur to trigger validation
    await emailInput.blur();
    await passwordInput.blur();
    await page.waitForTimeout(100);

    // Should show green checkmarks for both fields
    const emailFeedback = page.locator('input[name="email"]').locator('..').locator('..').locator('[role="alert"]');
    await expect(emailFeedback).toHaveClass(/text-green-600/);

    const passwordFeedback = page.locator('input[name="password"]').locator('..').locator('..').locator('[role="alert"]');
    await expect(passwordFeedback).toHaveClass(/text-green-600/);

    // Submit button should be enabled
    await expect(submitButton).toBeEnabled();

    // Should be able to submit (will navigate to dashboard or show auth error)
    await submitButton.click();

    // Should attempt to navigate (either success to dashboard or stay with auth error)
    // We're testing validation, not authentication, so either outcome is acceptable
    await page.waitForTimeout(1000);
  });

  test('should display validation errors with proper ARIA attributes for accessibility', async ({ page }) => {
    // Requirement 6.4: Validation feedback should be accessible
    await page.goto('/login');

    const emailInput = page.locator('input[name="email"]');
    const passwordInput = page.locator('input[name="password"]');

    // Trigger validation errors
    await emailInput.fill('invalid');
    await emailInput.blur();
    await page.waitForTimeout(100);

    // Check ARIA attributes on input
    await expect(emailInput).toHaveAttribute('aria-invalid', 'true');
    await expect(emailInput).toHaveAttribute('aria-describedby', 'email-feedback');

    // Check error message has proper role
    const emailError = page.locator('#email-feedback');
    await expect(emailError).toHaveAttribute('role', 'alert');
    await expect(emailError).toHaveAttribute('aria-live', 'polite');

    // Same for password
    await passwordInput.fill('short');
    await passwordInput.blur();
    await page.waitForTimeout(100);

    await expect(passwordInput).toHaveAttribute('aria-invalid', 'true');
    await expect(passwordInput).toHaveAttribute('aria-describedby', 'password-feedback');

    const passwordError = page.locator('#password-feedback');
    await expect(passwordError).toHaveAttribute('role', 'alert');
    await expect(passwordError).toHaveAttribute('aria-live', 'polite');
  });

  test('should handle rapid input changes gracefully', async ({ page }) => {
    // Test that validation doesn't break with rapid typing
    await page.goto('/login');

    const emailInput = page.locator('input[name="email"]');
    const passwordInput = page.locator('input[name="password"]');

    // Rapidly type and delete in email field - result in incomplete email
    await emailInput.fill('t');
    await emailInput.press('Backspace');
    await emailInput.fill('invalid');
    await emailInput.blur();
    await page.waitForTimeout(200);

    // Should show validation error for invalid email
    const emailError = page.locator('text=Please enter a valid email address');
    await expect(emailError).toBeVisible();

    // Rapidly type in password field
    await passwordInput.fill('abc');
    await passwordInput.press('Backspace');
    await passwordInput.fill('123');
    await passwordInput.blur();
    await page.waitForTimeout(200);

    // Should show validation error for short password
    const passwordError = page.locator('text=Password must be at least 8 characters');
    await expect(passwordError).toBeVisible();
  });

  test('should maintain validation state when switching between fields', async ({ page }) => {
    // Test that validation persists when moving between fields
    await page.goto('/login');

    const emailInput = page.locator('input[name="email"]');
    const passwordInput = page.locator('input[name="password"]');

    // Enter invalid email and move to password
    await emailInput.fill('invalid');
    await emailInput.blur();
    await page.waitForTimeout(100);

    // Email error should be visible
    let emailError = page.locator('text=Please enter a valid email address');
    await expect(emailError).toBeVisible();

    // Enter invalid password
    await passwordInput.fill('short');
    await passwordInput.blur();
    await page.waitForTimeout(100);

    // Both errors should be visible
    await expect(emailError).toBeVisible();
    const passwordError = page.locator('text=Password must be at least 8 characters');
    await expect(passwordError).toBeVisible();

    // Fix email
    await emailInput.fill('valid@example.com');
    await emailInput.blur();
    await page.waitForTimeout(100);

    // Email should show success, password should still show error
    const emailSuccess = page.locator('input[name="email"]').locator('..').locator('..').locator('[role="alert"]');
    await expect(emailSuccess).toHaveClass(/text-green-600/);
    await expect(passwordError).toBeVisible();

    // Fix password
    await passwordInput.fill('ValidPass123');
    await passwordInput.blur();
    await page.waitForTimeout(100);

    // Both should show success
    await expect(emailSuccess).toHaveClass(/text-green-600/);
    const passwordSuccess = page.locator('input[name="password"]').locator('..').locator('..').locator('[role="alert"]');
    await expect(passwordSuccess).toHaveClass(/text-green-600/);
  });

  test('should show validation errors in correct visual style', async ({ page }) => {
    // Requirement 6.4: Validation errors should be in red with error icon
    await page.goto('/login');

    const emailInput = page.locator('input[name="email"]');
    const passwordInput = page.locator('input[name="password"]');

    // Trigger validation errors
    await emailInput.fill('invalid');
    await passwordInput.fill('short');
    await emailInput.blur();
    await passwordInput.blur();
    await page.waitForTimeout(100);

    // Check email error styling
    const emailError = page.locator('input[name="email"]').locator('..').locator('..').locator('[role="alert"]');
    await expect(emailError).toHaveClass(/text-red-600/);
    
    // Should have AlertCircle icon
    const emailIcon = emailError.locator('svg').first();
    await expect(emailIcon).toBeVisible();

    // Check password error styling
    const passwordError = page.locator('input[name="password"]').locator('..').locator('..').locator('[role="alert"]');
    await expect(passwordError).toHaveClass(/text-red-600/);
    
    // Should have AlertCircle icon
    const passwordIcon = passwordError.locator('svg').first();
    await expect(passwordIcon).toBeVisible();

    // Input fields should have red border
    await expect(emailInput).toHaveClass(/border-red-500/);
    await expect(passwordInput).toHaveClass(/border-red-500/);
  });

  test('should show validation success in correct visual style', async ({ page }) => {
    // Requirement 6.5: Successful validation should show green checkmark
    await page.goto('/login');

    const emailInput = page.locator('input[name="email"]');
    const passwordInput = page.locator('input[name="password"]');

    // Enter valid data
    await emailInput.fill('valid@example.com');
    await passwordInput.fill('ValidPass123');
    await emailInput.blur();
    await passwordInput.blur();
    await page.waitForTimeout(100);

    // Check email success styling
    const emailSuccess = page.locator('input[name="email"]').locator('..').locator('..').locator('[role="alert"]');
    await expect(emailSuccess).toHaveClass(/text-green-600/);
    
    // Should have CheckCircle icon
    const emailIcon = emailSuccess.locator('svg').first();
    await expect(emailIcon).toBeVisible();

    // Check password success styling
    const passwordSuccess = page.locator('input[name="password"]').locator('..').locator('..').locator('[role="alert"]');
    await expect(passwordSuccess).toHaveClass(/text-green-600/);
    
    // Should have CheckCircle icon
    const passwordIcon = passwordSuccess.locator('svg').first();
    await expect(passwordIcon).toBeVisible();

    // Input fields should have green border
    await expect(emailInput).toHaveClass(/border-green-500/);
    await expect(passwordInput).toHaveClass(/border-green-500/);
  });
});
