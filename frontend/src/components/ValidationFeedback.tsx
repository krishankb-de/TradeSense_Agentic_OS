/**
 * ValidationFeedback Component
 * Displays validation messages with appropriate icons and colors
 */

import React from 'react';
import { CheckCircle, AlertCircle } from 'lucide-react';
import { ValidationResult } from '../services/types';

interface ValidationFeedbackProps {
  validation: ValidationResult;
  fieldId?: string;
}

export const ValidationFeedback: React.FC<ValidationFeedbackProps> = ({
  validation,
  fieldId,
}) => {
  if (!validation) return null;

  return (
    <div
      id={fieldId}
      className={`flex items-center mt-1 ${
        validation.isValid ? 'text-green-600' : 'text-red-600'
      }`}
      style={{ fontSize: 'var(--text-sm)' }}
      role="alert"
      aria-live="polite"
    >
      {validation.isValid ? (
        <CheckCircle className="w-4 h-4 mr-1" aria-hidden="true" />
      ) : (
        <AlertCircle className="w-4 h-4 mr-1" aria-hidden="true" />
      )}
      <span>{validation.error || 'Valid'}</span>
    </div>
  );
};
