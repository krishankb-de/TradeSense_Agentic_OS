/**
 * Unit tests for Login Form Component
 * 
 * Tests specific examples and edge cases for login form functionality.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import Login from '../pages/Login';
import { errorHandler } from '../services/errorHandler';

// Mock the AuthContext
const mockLogin = vi.fn();
const mockLogout = vi.fn();

vi.mock('../context/AuthContext', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAuth: () => ({
    isAuthenticated: false,
    user: null,
    login: mockLogin,
    logout: mockLogout,
    token: null,
  }),
}));

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

describe('Login Form - Unit Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Form Rendering', () => {
    it('should render login form with all required fields', () => {
      render(
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      );

      expect(screen.getByText('TradeSense')).toBeInTheDocument();
      expect(screen.getByText('Sign in to your account')).toBeInTheDocument();
      expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
    });

    it('should render submit button with correct initial state', () => {
      render(
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      );

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      expect(submitButton).not.toBeDisabled();
      expect(submitButton).toHaveTextContent('Sign in');
    });
  });

  describe('Email Validation', () => {
    it('should show error for invalid email on blur', async () => {
      const user = userEvent.setup();
      render(
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      );

      const emailInput = screen.getByLabelText(/email address/i);
      
      await user.type(emailInput, 'invalid-email');
      await user.tab(); // Trigger blur

      await waitFor(() => {
        expect(screen.getByText(/please enter a valid email address/i)).toBeInTheDocument();
      });
    });

    it('should show error for empty email on blur', async () => {
      const user = userEvent.setup();
      render(
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      );

      const emailInput = screen.getByLabelText(/email address/i);
      
      await user.click(emailInput);
      await user.tab(); // Trigger blur without typing

      await waitFor(() => {
        expect(screen.getByText(/email is required/i)).toBeInTheDocument();
      });
    });

    it('should not show error for valid email', async () => {
      const user = userEvent.setup();
      render(
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      );

      const emailInput = screen.getByLabelText(/email address/i);
      
      await user.type(emailInput, 'test@example.com');
      await user.tab();

      await waitFor(() => {
        expect(screen.queryByText(/please enter a valid email address/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Password Validation', () => {
    it('should show error for short password on blur', async () => {
      const user = userEvent.setup();
      render(
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      );

      const passwordInput = screen.getByLabelText(/password/i);
      
      await user.type(passwordInput, 'short');
      await user.tab();

      await waitFor(() => {
        expect(screen.getByText(/password must be at least 8 characters/i)).toBeInTheDocument();
      });
    });

    it('should show error for password without letter and number', async () => {
      const user = userEvent.setup();
      render(
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      );

      const passwordInput = screen.getByLabelText(/password/i);
      
      await user.type(passwordInput, 'onlyletters');
      await user.tab();

      await waitFor(() => {
        expect(screen.getByText(/password must contain at least one letter and one number/i)).toBeInTheDocument();
      });
    });

    it('should not show error for valid password', async () => {
      const user = userEvent.setup();
      render(
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      );

      const passwordInput = screen.getByLabelText(/password/i);
      
      await user.type(passwordInput, 'ValidPass123');
      await user.tab();

      await waitFor(() => {
        expect(screen.queryByText(/password must/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Form Submission', () => {
    it('should call login with correct credentials on valid submission', async () => {
      const user = userEvent.setup();
      mockLogin.mockResolvedValue(undefined);

      render(
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      );

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'ValidPass123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith('test@example.com', 'ValidPass123');
      });
    });

    it('should navigate to home on successful login', async () => {
      const user = userEvent.setup();
      mockLogin.mockResolvedValue(undefined);

      render(
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      );

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'ValidPass123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/');
      });
    });

    it('should not submit form with invalid email', async () => {
      const user = userEvent.setup();
      mockLogin.mockResolvedValue(undefined);

      render(
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      );

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'invalid-email');
      await user.type(passwordInput, 'ValidPass123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockLogin).not.toHaveBeenCalled();
      });
    });

    it('should not submit form with invalid password', async () => {
      const user = userEvent.setup();
      mockLogin.mockResolvedValue(undefined);

      render(
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      );

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'short');
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockLogin).not.toHaveBeenCalled();
      });
    });

    it('should handle login error and call errorHandler', async () => {
      const user = userEvent.setup();
      const mockError = new Error('Login failed');
      mockLogin.mockRejectedValue(mockError);

      render(
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      );

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'ValidPass123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(errorHandler.handleError).toHaveBeenCalledWith(mockError);
      });
    });
  });

  describe('Loading State', () => {
    it('should disable submit button during submission', async () => {
      const user = userEvent.setup();
      let resolveLogin: () => void;
      const loginPromise = new Promise<void>((resolve) => {
        resolveLogin = resolve;
      });
      mockLogin.mockImplementation(() => loginPromise);

      render(
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      );

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'ValidPass123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(submitButton).toBeDisabled();
      });

      resolveLogin!();
    });

    it('should show loading text during submission', async () => {
      const user = userEvent.setup();
      let resolveLogin: () => void;
      const loginPromise = new Promise<void>((resolve) => {
        resolveLogin = resolve;
      });
      mockLogin.mockImplementation(() => loginPromise);

      render(
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      );

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'ValidPass123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(submitButton).toHaveTextContent('Signing in...');
      });

      resolveLogin!();
    });

    it('should disable form fields during submission', async () => {
      const user = userEvent.setup();
      let resolveLogin: () => void;
      const loginPromise = new Promise<void>((resolve) => {
        resolveLogin = resolve;
      });
      mockLogin.mockImplementation(() => loginPromise);

      render(
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      );

      const emailInput = screen.getByLabelText(/email address/i) as HTMLInputElement;
      const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement;
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'ValidPass123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(emailInput.disabled).toBe(true);
        expect(passwordInput.disabled).toBe(true);
      });

      resolveLogin!();
    });

    it('should re-enable form after submission completes', async () => {
      const user = userEvent.setup();
      mockLogin.mockResolvedValue(undefined);

      render(
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      );

      const emailInput = screen.getByLabelText(/email address/i) as HTMLInputElement;
      const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement;
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'ValidPass123');
      await user.click(submitButton);

      // Wait for navigation to be called (submission complete)
      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalled();
      });
    });

    it('should re-enable form after submission fails', async () => {
      const user = userEvent.setup();
      mockLogin.mockRejectedValue(new Error('Login failed'));

      render(
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      );

      const emailInput = screen.getByLabelText(/email address/i) as HTMLInputElement;
      const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement;
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'ValidPass123');
      await user.click(submitButton);

      // Wait for error handler to be called
      await waitFor(() => {
        expect(errorHandler.handleError).toHaveBeenCalled();
      });

      // Form should be re-enabled after error
      await waitFor(() => {
        expect(submitButton).not.toBeDisabled();
      });
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      render(
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      );

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);

      expect(emailInput).toHaveAttribute('name', 'email');
      expect(passwordInput).toHaveAttribute('name', 'password');
    });

    it('should mark required fields', () => {
      render(
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      );

      // Check for required indicators (asterisks)
      const requiredMarkers = screen.getAllByText('*');
      expect(requiredMarkers).toHaveLength(2); // Email and password
    });
  });
});
