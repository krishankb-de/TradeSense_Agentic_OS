import { ReactNode } from 'react';

interface ResponsiveGridProps {
  children: ReactNode;
  className?: string;
}

/**
 * ResponsiveGrid component with mobile-first design
 * - 1 column on mobile (< 640px)
 * - 2 columns on tablet (>= 640px)
 * - 4 columns on desktop (>= 1024px)
 * 
 * Validates: Requirements 8.2, 8.3
 */
export function ResponsiveGrid({ children, className = '' }: ResponsiveGridProps) {
  return (
    <div className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 ${className}`}>
      {children}
    </div>
  );
}
