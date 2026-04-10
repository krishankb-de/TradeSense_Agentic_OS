import React from 'react';
import { Skeleton } from './Skeleton';

/**
 * Skeleton component for stat cards on the dashboard
 * Matches the layout of the actual stat card component
 */
export const StatCardSkeleton: React.FC = () => {
  return (
    <div 
      className="bg-white overflow-hidden"
      style={{
        borderRadius: 'var(--radius-lg)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      <div className="p-5">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <Skeleton 
              variant="rectangular" 
              width={48} 
              height={48} 
              className="rounded-md" 
            />
          </div>
          <div className="ml-5 w-0 flex-1">
            <Skeleton variant="text" width="60%" height={14} className="mb-2" />
            <Skeleton variant="text" width="40%" height={20} />
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * Skeleton component for table rows
 * Used in lists like Leads, Jobs, and Technicians
 */
export const TableRowSkeleton: React.FC<{ columns: number }> = ({ columns }) => {
  return (
    <tr className="border-b border-gray-200">
      {Array.from({ length: columns }).map((_, index) => (
        <td key={index} className="px-6 py-4">
          <Skeleton variant="text" width="80%" height={16} />
        </td>
      ))}
    </tr>
  );
};

/**
 * Skeleton component for forms
 * Displays loading state for form fields
 */
export const FormSkeleton: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Form field 1 */}
      <div>
        <Skeleton variant="text" width={100} height={14} className="mb-2" />
        <Skeleton variant="rectangular" width="100%" height={40} />
      </div>
      
      {/* Form field 2 */}
      <div>
        <Skeleton variant="text" width={120} height={14} className="mb-2" />
        <Skeleton variant="rectangular" width="100%" height={40} />
      </div>
      
      {/* Form field 3 */}
      <div>
        <Skeleton variant="text" width={80} height={14} className="mb-2" />
        <Skeleton variant="rectangular" width="100%" height={80} />
      </div>
      
      {/* Submit button */}
      <div className="flex justify-end">
        <Skeleton 
          variant="rectangular" 
          width={120} 
          height={40} 
          className="rounded-md" 
        />
      </div>
    </div>
  );
};

/**
 * Skeleton component for the entire dashboard
 * Displays loading state for all dashboard stat cards
 */
export const DashboardSkeleton: React.FC = () => {
  return (
    <div>
      <Skeleton variant="text" width={150} height={32} className="mb-6" />
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <StatCardSkeleton />
        <StatCardSkeleton />
        <StatCardSkeleton />
        <StatCardSkeleton />
      </div>
    </div>
  );
};
