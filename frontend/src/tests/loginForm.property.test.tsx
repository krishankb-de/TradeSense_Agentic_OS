/**
 * Property-based tests for Login Form Component
 * 
 * These tests verify correctness properties across many randomly generated inputs.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import fc from 'fast-check';
import Login from '../pages/Login';
import { AuthProvider } from '../context/AuthContext';
import { getPropertyTestConfig } from './propertyTestConfig';

// Mock the AuthContext
const mockLogin = vi.fn();
const mockLogout = vi.fn();

vi.mock('../context/AuthContext', async () => {
  const actual = await vi.importActual('../context/AuthContext');
  return {
    ...actual,
    useAuth: () => ({
      isAuthenticated: false,
      user: null,
      login: mockLogin,
      logout: mockLogout,
      token: null,
    }),
  };
});

// Mock the errorHandler
vi.mock('../services/errorHandler', () => ({
  errorHandler: {
    handleError: vi.fn(),
    showToast: vi.fn(),
    getErrorMessage: vi.fn(),
    logError: vi.fn(),
  },
}));

// Mock react-router-dom navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('Login Form - Property-Based Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  /**
   * Property 14: Form Submission State
   * 
   * **Validates: Requirements 5.2**
   * 
   * For any form during submission, the submit button should be disabled 
   * and display a loading indicator.
   */
  it('Property 14: Submit button disabled during submission', async () => {
    // Generate arbitrary valid email and password combinations (alphanumeric only)
    const emailArb = fc.string({ minLength: 5, maxLength: 15 })
      .filter(s => /^[a-zA-Z0-9]+$/.test(s))
      .map(s => `${s}@test.com`);
    // Password must be at least 8 characters with letters and numbers
    const passwordArb = fc.tuple(
      fc.string({ minLength: 5, maxLength: 12 }).filter(s => /^[a-zA-Z]+$/.test(s)),
      fc.integer({ min: 1000, max: 9999 })
    ).map(([letters, num]) => `${letters}${num}`); // This ensures at least 9 characters

    await fc.assert(
      fc.asyncProperty(emailArb, passwordArb, async (email, password) => {
        // Mock login to simulate async operation
        let resolveLogin: () => void;
        const loginPromise = new Promise<void>((resolve) => {
          resolveLogin = resolve;
        });
        
        mockLogin.mockImplementation(() => loginPromise);

        const { unmount } = render(
          <BrowserRouter>
            <Login />
          </BrowserRouter>
        );

        // Get form elements
        const emailInput = screen.getByLabelText(/email address/i);
        const passwordInput = screen.getByLabelText(/password/i);
        const submitButton = screen.getByTestId('login-submit-button');

        // Fill in the form with valid data using fireEvent (faster than userEvent)
        fireEvent.change(emailInput, { target: { value: email } });
        fireEvent.change(passwordInput, { target: { value: password } });

        // Trigger form submission
        fireEvent.click(submitButton);

        // During submission, button should be disabled
        await waitFor(() => {
          expect(submitButton).toBeDisabled();
        }, { timeout: 500 });
        
        // Button should show loading text
        expect(submitButton.textContent).toContain('Signing in...');

        // Resolve the login promise
        resolveLogin!();
        
        // Wait for submission to complete
        await waitFor(() => {
          expect(mockLogin).toHaveBeenCalled();
        }, { timeout: 500 });

        unmount();
      }),
      { ...getPropertyTestConfig('dev'), numRuns: 10, timeout: 5000 }
    );
  });

  /**
   * Property: Loading indicator displayed during submission
   * 
   * For any form during submission, a loading spinner should be visible.
   */
  it('Property: Loading spinner visible during submission', async () => {
    const emailArb = fc.string({ minLength: 5, maxLength: 15 })
      .filter(s => /^[a-zA-Z0-9]+$/.test(s))
      .map(s => `${s}@test.com`);
    const passwordArb = fc.tuple(
      fc.string({ minLength: 5, maxLength: 12 }).filter(s => /^[a-zA-Z]+$/.test(s)),
      fc.integer({ min: 1000, max: 9999 })
    ).map(([letters, num]) => `${letters}${num}`);

    await fc.assert(
      fc.asyncProperty(emailArb, passwordArb, async (email, password) => {
        // Mock login to simulate async operation
        let resolveLogin: () => void;
        const loginPromise = new Promise<void>((resolve) => {
          resolveLogin = resolve;
        });
        
        mockLogin.mockImplementation(() => loginPromise);

        const { unmount, container } = render(
          <BrowserRouter>
            <Login />
          </BrowserRouter>
        );

        const emailInput = screen.getByLabelText(/email address/i);
        const passwordInput = screen.getByLabelText(/password/i);
        const submitButton = screen.getByTestId('login-submit-button');

        fireEvent.change(emailInput, { target: { value: email } });
        fireEvent.change(passwordInput, { target: { value: password } });
        fireEvent.click(submitButton);

        await waitFor(() => {
          // Check for loading spinner (Loader2 component with animate-spin class)
          const spinner = container.querySelector('.animate-spin');
          expect(spinner).toBeTruthy();
        }, { timeout: 500 });

        resolveLogin!();
        await waitFor(() => {
          expect(mockLogin).toHaveBeenCalled();
        }, { timeout: 500 });

        unmount();
      }),
      { ...getPropertyTestConfig('dev'), numRuns: 10, timeout: 5000 }
    );
  });

  /**
   * Property: Form fields disabled during submission
   * 
   * For any form during submission, all form fields should be disabled
   * to prevent user input.
   */
  it('Property: Form fields disabled during submission', async () => {
    const emailArb = fc.string({ minLength: 5, maxLength: 15 })
      .filter(s => /^[a-zA-Z0-9]+$/.test(s))
      .map(s => `${s}@test.com`);
    const passwordArb = fc.tuple(
      fc.string({ minLength: 5, maxLength: 12 }).filter(s => /^[a-zA-Z]+$/.test(s)),
      fc.integer({ min: 1000, max: 9999 })
    ).map(([letters, num]) => `${letters}${num}`);

    await fc.assert(
      fc.asyncProperty(emailArb, passwordArb, async (email, password) => {
        let resolveLogin: () => void;
        const loginPromise = new Promise<void>((resolve) => {
          resolveLogin = resolve;
        });
        
        mockLogin.mockImplementation(() => loginPromise);

        const { unmount } = render(
          <BrowserRouter>
            <Login />
          </BrowserRouter>
        );

        const emailInput = screen.getByLabelText(/email address/i) as HTMLInputElement;
        const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement;
        const submitButton = screen.getByTestId('login-submit-button');

        fireEvent.change(emailInput, { target: { value: email } });
        fireEvent.change(passwordInput, { target: { value: password } });
        fireEvent.click(submitButton);

        await waitFor(() => {
          // All form fields should be disabled during submission
          expect(emailInput.disabled).toBe(true);
          expect(passwordInput.disabled).toBe(true);
          expect(submitButton).toBeDisabled();
        }, { timeout: 500 });

        resolveLogin!();
        await waitFor(() => {
          expect(mockLogin).toHaveBeenCalled();
        }, { timeout: 500 });

        unmount();
      }),
      { ...getPropertyTestConfig('dev'), numRuns: 10, timeout: 5000 }
    );
  });
});

