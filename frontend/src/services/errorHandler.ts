/**
 * Error Handler Service
 * Centralized error processing and user notification
 */

import { ErrorHandler, ToastType, ToastOptions, ErrorCategory, ERROR_MESSAGES, NETWORK_ERROR } from './types';

class ErrorHandlerImpl implements ErrorHandler {
  private toastCallbacks: Array<(message: string, type: ToastType, options?: ToastOptions) => void> = [];

  // Register toast callback (will be set by toast component)
  registerToastCallback(callback: (message: string, type: ToastType, options?: ToastOptions) => void): void {
    this.toastCallbacks.push(callback);
  }

  handleError(error: Error | any): void {
    const message = this.getErrorMessage(error);
    this.showToast(message, 'error');
    this.logError(error);
  }

  showToast(message: string, type: ToastType, options?: ToastOptions): void {
    // Notify all registered callbacks
    this.toastCallbacks.forEach(callback => callback(message, type, options));
  }

  getErrorMessage(error: Error | any): string {
    // Check if it's an Axios error
    if (error.response) {
      const status = error.response.status;
      return ERROR_MESSAGES[status] || 'An unexpected error occurred.';
    }

    // Check for network errors
    if (error.code === 'ERR_NETWORK' || error.message === 'Network Error') {
      return NETWORK_ERROR;
    }

    // Check for timeout
    if (error.code === 'ECONNABORTED') {
      return 'Request timed out. Please try again.';
    }

    // Default error message
    return error.message || 'An unexpected error occurred.';
  }

  logError(error: Error, context?: any): void {
    const errorLog = {
      timestamp: new Date().toISOString(),
      message: error.message,
      stack: error.stack,
      context,
    };

    console.error('[TradeSense Error]', errorLog);

    // In production, send to error tracking service
    if (import.meta.env.PROD) {
      // TODO: Implement error tracking service integration
    }
  }

  private categorizeError(error: any): ErrorCategory {
    if (error.response) {
      const status = error.response.status;
      if (status === 401) return ErrorCategory.AUTHENTICATION;
      if (status === 403) return ErrorCategory.AUTHORIZATION;
      if (status >= 400 && status < 500) return ErrorCategory.CLIENT;
      if (status >= 500) return ErrorCategory.SERVER;
    }
    return ErrorCategory.NETWORK;
  }
}

// Export singleton instance
export const errorHandler = new ErrorHandlerImpl();
