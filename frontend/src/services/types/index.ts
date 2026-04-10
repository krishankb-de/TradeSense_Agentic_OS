/**
 * Core service type definitions for TradeSense frontend
 */

// ============================================================================
// Token Management Types
// ============================================================================

export interface TokenPayload {
  sub: string;        // Subject (user email)
  exp: number;        // Expiration time (Unix timestamp)
  iat: number;        // Issued at (Unix timestamp)
  role: string;       // User role
  jti?: string;       // JWT ID (optional)
}

export interface TokenManager {
  // Token storage
  storeTokens(accessToken: string, refreshToken: string): void;
  getAccessToken(): string | null;
  getRefreshToken(): string | null;
  clearTokens(): void;
  
  // Token validation
  isTokenValid(token: string): boolean;
  isTokenExpiringSoon(token: string, thresholdMinutes: number): boolean;
  decodeToken(token: string): TokenPayload | null;
  
  // Token refresh
  refreshAccessToken(): Promise<string>;
  scheduleTokenRefresh(): void;
  cancelTokenRefresh(): void;
}

// ============================================================================
// API Client Types
// ============================================================================

export interface APIClient {
  // HTTP methods
  get<T>(url: string, config?: RequestConfig): Promise<T>;
  post<T>(url: string, data?: any, config?: RequestConfig): Promise<T>;
  put<T>(url: string, data?: any, config?: RequestConfig): Promise<T>;
  delete<T>(url: string, config?: RequestConfig): Promise<T>;
  
  // Configuration
  setBaseURL(url: string): void;
  setTimeout(ms: number): void;
  
  // Cache management
  clearCache(): void;
  getCacheKey(url: string, params?: any): string;
}

export interface RequestConfig {
  headers?: Record<string, string>;
  params?: Record<string, any>;
  timeout?: number;
  cache?: boolean;
}

export interface RequestCache {
  data: any;
  timestamp: number;
  expiresIn: number;
}

// ============================================================================
// Error Handling Types
// ============================================================================

export type ToastType = 'error' | 'warning' | 'success' | 'info';

export interface ToastMessage {
  id: string;
  message: string;
  type: ToastType;
  duration: number;
  dismissible: boolean;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export interface ErrorHandler {
  handleError(error: Error | any): void;
  showToast(message: string, type: ToastType, options?: ToastOptions): void;
  getErrorMessage(error: Error | any): string;
  logError(error: Error, context?: any): void;
}

export interface ToastOptions {
  duration?: number;
  dismissible?: boolean;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export enum ErrorCategory {
  AUTHENTICATION = 'authentication',
  AUTHORIZATION = 'authorization',
  CLIENT = 'client',
  SERVER = 'server',
  NETWORK = 'network'
}

// ============================================================================
// Mock Data Provider Types
// ============================================================================

export interface Lead {
  id: string;
  name: string;
  email: string;
  phone: string;
  status: 'new' | 'contacted' | 'qualified' | 'converted';
  source: string;
  created_at: string;
}

export interface Job {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'active' | 'completed' | 'cancelled';
  technician_id: string | null;
  lead_id: string;
  scheduled_date: string;
  completion_date: string | null;
}

export interface Technician {
  id: string;
  name: string;
  email: string;
  phone: string;
  skills: string[];
  available: boolean;
  rating: number;
}

export interface MockDataProvider {
  isEnabled(): boolean;
  setEnabled(enabled: boolean): void;
  
  // Data generators
  generateLeads(count: number): Lead[];
  generateJobs(count: number): Job[];
  generateTechnicians(count: number): Technician[];
  
  // Utility
  shouldUseMockData(realData: any[]): boolean;
}

// ============================================================================
// Form Validation Types
// ============================================================================

export interface ValidationResult {
  isValid: boolean;
  error?: string;
}

export interface FormValidator {
  validateEmail(email: string): ValidationResult;
  validatePassword(password: string): ValidationResult;
  validateRequired(value: any): ValidationResult;
  validatePhone(phone: string): ValidationResult;
  validateLength(value: string, min: number, max: number): ValidationResult;
}

export interface FormFieldProps {
  label: string;
  name: string;
  type: string;
  value: string;
  onChange: (value: string) => void;
  onBlur?: () => void;
  validation?: ValidationResult;
  required?: boolean;
  disabled?: boolean;
}

export interface FormState<T> {
  values: T;
  errors: Partial<Record<keyof T, string>>;
  touched: Partial<Record<keyof T, boolean>>;
  isSubmitting: boolean;
  isValid: boolean;
}

export interface FormConfig<T> {
  initialValues: T;
  validationSchema: ValidationSchema<T>;
  onSubmit: (values: T) => Promise<void>;
  validateOnChange?: boolean;
  validateOnBlur?: boolean;
}

export type ValidationSchema<T> = {
  [K in keyof T]?: (value: T[K]) => ValidationResult;
};

// ============================================================================
// User Profile Types
// ============================================================================

export interface User {
  email: string;
  role: string;
  name?: string;
  avatar?: string;
}

export interface ProfileMenuItem {
  label: string;
  icon: React.ComponentType;
  onClick: () => void;
  variant?: 'default' | 'danger';
}

// ============================================================================
// Dashboard Types
// ============================================================================

export interface Stats {
  total_leads: number;
  active_jobs: number;
  available_technicians: number;
  completion_rate: number;
}

export interface StatCard {
  name: string;
  value: string | number;
  icon: React.ComponentType;
  color: string;
  trend?: {
    value: number;
    direction: 'up' | 'down';
  };
}

// ============================================================================
// Storage Keys
// ============================================================================

export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'tradesense_access_token',
  REFRESH_TOKEN: 'tradesense_refresh_token',
  TOKEN_EXPIRY: 'tradesense_token_expiry',
  USER_DATA: 'tradesense_user_data',
  MOCK_DATA_ENABLED: 'tradesense_mock_data_enabled',
} as const;

// ============================================================================
// Error Messages
// ============================================================================

export const ERROR_MESSAGES: Record<number, string> = {
  401: 'Your session has expired. Please log in again.',
  403: "You don't have permission to perform this action.",
  404: 'The requested resource was not found.',
  500: 'Server error occurred. Please try again later.',
  503: 'Service temporarily unavailable. Please try again later.',
};

export const NETWORK_ERROR = 'Unable to connect to server. Please check your connection.';
