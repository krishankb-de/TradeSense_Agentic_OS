/**
 * FormField Component
 * Reusable form field with integrated validation feedback
 */

import React from 'react';
import { FormFieldProps } from '../services/types';
import { ValidationFeedback } from './ValidationFeedback';

export const FormField: React.FC<FormFieldProps> = ({
  label,
  name,
  type,
  value,
  onChange,
  onBlur,
  validation,
  required = false,
  disabled = false,
}) => {
  const hasError = validation && !validation.isValid;
  const isValid = validation && validation.isValid && value.length > 0;

  return (
    <div className="mb-4">
      <label
        htmlFor={name}
        className="block font-medium text-gray-700 mb-1"
        style={{ fontSize: 'var(--text-sm)' }}
      >
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      <div className="relative">
        <input
          id={name}
          name={name}
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onBlur={onBlur}
          disabled={disabled}
          required={required}
          className={`
            w-full px-3 py-2 border rounded-md
            focus:outline-none focus:ring-2 focus:ring-offset-1
            disabled:bg-gray-100 disabled:cursor-not-allowed
            transition-colors
            ${hasError ? 'border-red-500 focus:ring-red-500' : ''}
            ${isValid ? 'border-green-500 focus:ring-green-500' : ''}
            ${!hasError && !isValid ? 'border-gray-300 focus:ring-blue-500' : ''}
          `}
          style={{
            boxShadow: 'var(--shadow-sm)',
            borderRadius: 'var(--radius-md)',
            transitionDuration: 'var(--transition-base)',
          }}
          aria-invalid={hasError}
          aria-required={required}
          aria-describedby={validation ? `${name}-feedback` : undefined}
        />
      </div>
      {validation && (
        <ValidationFeedback validation={validation} fieldId={`${name}-feedback`} />
      )}
    </div>
  );
};
