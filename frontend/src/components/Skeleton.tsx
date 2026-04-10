import React from 'react';

export interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  variant?: 'text' | 'circular' | 'rectangular';
  animation?: 'pulse' | 'wave' | 'none';
  className?: string;
}

/**
 * Base Skeleton component for loading states
 * Provides visual feedback during data loading with content-shaped placeholders
 */
export const Skeleton: React.FC<SkeletonProps> = ({
  width = '100%',
  height = '1rem',
  variant = 'rectangular',
  animation = 'wave',
  className = '',
}) => {
  const getVariantClass = () => {
    switch (variant) {
      case 'text':
        return 'rounded';
      case 'circular':
        return 'rounded-full';
      case 'rectangular':
      default:
        return 'rounded-md';
    }
  };

  const getAnimationClass = () => {
    switch (animation) {
      case 'pulse':
        return 'animate-pulse';
      case 'wave':
        return 'skeleton-wave';
      case 'none':
      default:
        return '';
    }
  };

  const style: React.CSSProperties = {
    width: typeof width === 'number' ? `${width}px` : width,
    height: typeof height === 'number' ? `${height}px` : height,
    backgroundColor: 'var(--color-gray-200)',
    borderRadius: variant === 'circular' ? 'var(--radius-full)' : 'var(--radius-md)',
  };

  return (
    <div
      className={`${getVariantClass()} ${getAnimationClass()} ${className}`}
      style={style}
      aria-busy="true"
      aria-live="polite"
      role="status"
    >
      <span className="sr-only">Loading...</span>
    </div>
  );
};

export default Skeleton;
