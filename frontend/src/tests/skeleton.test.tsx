/**
 * Unit tests for Loading Skeleton Components
 * Feature: frontend-auth-and-ux-improvements
 * 
 * Tests specific examples and edge cases for skeleton components
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Skeleton } from '../components/Skeleton';
import { StatCardSkeleton, TableRowSkeleton, FormSkeleton, DashboardSkeleton } from '../components/SkeletonComponents';

describe('Skeleton Component', () => {
  describe('Basic Rendering', () => {
    it('should render with default props', () => {
      const { container } = render(<Skeleton />);
      const skeleton = container.querySelector('[role="status"]');
      
      expect(skeleton).toBeTruthy();
      expect(skeleton?.getAttribute('aria-busy')).toBe('true');
      expect(skeleton?.getAttribute('aria-live')).toBe('polite');
    });

    it('should render with custom width and height as numbers', () => {
      const { container } = render(<Skeleton width={200} height={50} />);
      const skeleton = container.querySelector('[role="status"]') as HTMLElement;
      
      expect(skeleton.style.width).toBe('200px');
      expect(skeleton.style.height).toBe('50px');
    });

    it('should render with custom width and height as strings', () => {
      const { container } = render(<Skeleton width="75%" height="2rem" />);
      const skeleton = container.querySelector('[role="status"]') as HTMLElement;
      
      expect(skeleton.style.width).toBe('75%');
      expect(skeleton.style.height).toBe('2rem');
    });

    it('should include screen reader text', () => {
      render(<Skeleton />);
      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });
  });

  describe('Variants', () => {
    it('should apply text variant styling', () => {
      const { container } = render(<Skeleton variant="text" />);
      const skeleton = container.querySelector('[role="status"]');
      
      expect(skeleton?.classList.contains('rounded')).toBe(true);
    });

    it('should apply circular variant styling', () => {
      const { container } = render(<Skeleton variant="circular" />);
      const skeleton = container.querySelector('[role="status"]');
      
      expect(skeleton?.classList.contains('rounded-full')).toBe(true);
    });

    it('should apply rectangular variant styling (default)', () => {
      const { container } = render(<Skeleton variant="rectangular" />);
      const skeleton = container.querySelector('[role="status"]');
      
      expect(skeleton?.classList.contains('rounded-md')).toBe(true);
    });
  });

  describe('Animations', () => {
    it('should apply pulse animation', () => {
      const { container } = render(<Skeleton animation="pulse" />);
      const skeleton = container.querySelector('[role="status"]');
      
      expect(skeleton?.classList.contains('animate-pulse')).toBe(true);
    });

    it('should apply wave animation (default)', () => {
      const { container } = render(<Skeleton animation="wave" />);
      const skeleton = container.querySelector('[role="status"]');
      
      expect(skeleton?.classList.contains('skeleton-wave')).toBe(true);
    });

    it('should apply no animation when set to none', () => {
      const { container } = render(<Skeleton animation="none" />);
      const skeleton = container.querySelector('[role="status"]');
      
      expect(skeleton?.classList.contains('animate-pulse')).toBe(false);
      expect(skeleton?.classList.contains('skeleton-wave')).toBe(false);
    });
  });

  describe('Custom className', () => {
    it('should apply custom className', () => {
      const { container } = render(<Skeleton className="custom-class" />);
      const skeleton = container.querySelector('[role="status"]');
      
      expect(skeleton?.classList.contains('custom-class')).toBe(true);
    });
  });
});

describe('StatCardSkeleton Component', () => {
  it('should render with card structure', () => {
    const { container } = render(<StatCardSkeleton />);
    
    const card = container.querySelector('.bg-white');
    expect(card).toBeTruthy();
  });

  it('should render icon skeleton', () => {
    const { container } = render(<StatCardSkeleton />);
    
    const skeletons = container.querySelectorAll('[role="status"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('should render text skeletons for label and value', () => {
    const { container } = render(<StatCardSkeleton />);
    
    // Should have multiple skeleton elements
    const skeletons = container.querySelectorAll('[role="status"]');
    expect(skeletons.length).toBeGreaterThanOrEqual(3); // icon + label + value
  });
});

describe('TableRowSkeleton Component', () => {
  it('should render with 1 column', () => {
    const { container } = render(
      <table>
        <tbody>
          <TableRowSkeleton columns={1} />
        </tbody>
      </table>
    );
    
    const cells = container.querySelectorAll('td');
    expect(cells.length).toBe(1);
  });

  it('should render with 5 columns', () => {
    const { container } = render(
      <table>
        <tbody>
          <TableRowSkeleton columns={5} />
        </tbody>
      </table>
    );
    
    const cells = container.querySelectorAll('td');
    expect(cells.length).toBe(5);
  });

  it('should render skeleton in each cell', () => {
    const { container } = render(
      <table>
        <tbody>
          <TableRowSkeleton columns={3} />
        </tbody>
      </table>
    );
    
    const cells = container.querySelectorAll('td');
    cells.forEach(cell => {
      const skeleton = cell.querySelector('[role="status"]');
      expect(skeleton).toBeTruthy();
    });
  });

  it('should have proper table row styling', () => {
    const { container } = render(
      <table>
        <tbody>
          <TableRowSkeleton columns={2} />
        </tbody>
      </table>
    );
    
    const row = container.querySelector('tr');
    expect(row?.classList.contains('border-b')).toBe(true);
    expect(row?.classList.contains('border-gray-200')).toBe(true);
  });
});

describe('FormSkeleton Component', () => {
  it('should render multiple form field skeletons', () => {
    const { container } = render(<FormSkeleton />);
    
    const skeletons = container.querySelectorAll('[role="status"]');
    expect(skeletons.length).toBeGreaterThan(3);
  });

  it('should have proper spacing between fields', () => {
    const { container } = render(<FormSkeleton />);
    
    const formContainer = container.querySelector('.space-y-6');
    expect(formContainer).toBeTruthy();
  });

  it('should render submit button skeleton', () => {
    const { container } = render(<FormSkeleton />);
    
    const buttonContainer = container.querySelector('.flex.justify-end');
    expect(buttonContainer).toBeTruthy();
    
    const buttonSkeleton = buttonContainer?.querySelector('[role="status"]');
    expect(buttonSkeleton).toBeTruthy();
  });
});

describe('DashboardSkeleton Component', () => {
  it('should render title skeleton', () => {
    const { container } = render(<DashboardSkeleton />);
    
    // First skeleton should be the title
    const skeletons = container.querySelectorAll('[role="status"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('should render 4 stat card skeletons', () => {
    const { container } = render(<DashboardSkeleton />);
    
    const cards = container.querySelectorAll('.bg-white.overflow-hidden');
    expect(cards.length).toBe(4);
  });

  it('should have responsive grid layout', () => {
    const { container } = render(<DashboardSkeleton />);
    
    const grid = container.querySelector('.grid');
    expect(grid?.classList.contains('grid-cols-1')).toBe(true);
    expect(grid?.classList.contains('sm:grid-cols-2')).toBe(true);
    expect(grid?.classList.contains('lg:grid-cols-4')).toBe(true);
  });

  it('should have proper spacing', () => {
    const { container } = render(<DashboardSkeleton />);
    
    const grid = container.querySelector('.grid');
    expect(grid?.classList.contains('gap-5')).toBe(true);
  });
});

describe('Accessibility', () => {
  it('should have proper ARIA attributes on all skeleton types', () => {
    const components = [
      <Skeleton key="1" />,
      <StatCardSkeleton key="2" />,
      <FormSkeleton key="3" />,
      <DashboardSkeleton key="4" />,
    ];

    components.forEach(component => {
      const { container } = render(component);
      const skeletons = container.querySelectorAll('[role="status"]');
      
      skeletons.forEach(skeleton => {
        expect(skeleton.getAttribute('aria-busy')).toBe('true');
        expect(skeleton.getAttribute('aria-live')).toBe('polite');
      });
    });
  });

  it('should have screen reader text for all skeletons', () => {
    const { container } = render(<DashboardSkeleton />);
    
    const srTexts = container.querySelectorAll('.sr-only');
    expect(srTexts.length).toBeGreaterThan(0);
    
    srTexts.forEach(srText => {
      expect(srText.textContent).toBe('Loading...');
    });
  });
});

describe('Edge Cases', () => {
  it('should handle zero columns in TableRowSkeleton', () => {
    const { container } = render(
      <table>
        <tbody>
          <TableRowSkeleton columns={0} />
        </tbody>
      </table>
    );
    
    const cells = container.querySelectorAll('td');
    expect(cells.length).toBe(0);
  });

  it('should handle very large dimensions', () => {
    const { container } = render(<Skeleton width={10000} height={5000} />);
    const skeleton = container.querySelector('[role="status"]') as HTMLElement;
    
    expect(skeleton.style.width).toBe('10000px');
    expect(skeleton.style.height).toBe('5000px');
  });

  it('should handle very small dimensions', () => {
    const { container } = render(<Skeleton width={1} height={1} />);
    const skeleton = container.querySelector('[role="status"]') as HTMLElement;
    
    expect(skeleton.style.width).toBe('1px');
    expect(skeleton.style.height).toBe('1px');
  });
});
