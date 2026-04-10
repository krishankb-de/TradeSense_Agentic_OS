import { useEffect, useState, useMemo, useCallback, memo } from 'react';
import { apiClient } from '../services/apiClient';
import { mockDataProvider } from '../services/mockDataProvider';
import { Users, Briefcase, UserCheck, TrendingUp, Database } from 'lucide-react';
import { DashboardSkeleton } from '../components/SkeletonComponents';
import { ResponsiveGrid } from '../components/ResponsiveGrid';
import { Stats, Lead, Job, Technician } from '../services/types';

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [usingMockData, setUsingMockData] = useState(false);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    try {
      // Fetch data from API
      const [leads, jobs, technicians] = await Promise.all([
        apiClient.get<Lead[]>('/leads'),
        apiClient.get<Job[]>('/jobs'),
        apiClient.get<Technician[]>('/technicians'),
      ]);

      // Check if we should use mock data
      const shouldUseMock = mockDataProvider.shouldUseMockData(leads);
      setUsingMockData(shouldUseMock);

      let finalLeads = leads;
      let finalJobs = jobs;
      let finalTechnicians = technicians;

      if (shouldUseMock) {
        // Generate mock data
        finalLeads = mockDataProvider.generateLeads(15);
        finalJobs = mockDataProvider.generateJobs(8);
        finalTechnicians = mockDataProvider.generateTechnicians(5);
      }

      // Calculate stats from actual or mock data
      const activeJobsCount = finalJobs.filter((j) => j.status === 'active').length;
      const availableTechsCount = finalTechnicians.filter((t) => t.available).length;
      const completedJobs = finalJobs.filter((j) => j.status === 'completed').length;
      const completionRate = finalJobs.length > 0 
        ? Math.round((completedJobs / finalJobs.length) * 100) 
        : 0;

      setStats({
        total_leads: finalLeads.length,
        active_jobs: activeJobsCount,
        available_technicians: availableTechsCount,
        completion_rate: completionRate,
      });
    } catch (error) {
      console.error('Failed to fetch stats:', error);
      // Set empty stats on error
      setStats({
        total_leads: 0,
        active_jobs: 0,
        available_technicians: 0,
        completion_rate: 0,
      });
    } finally {
      setLoading(false);
    }
  }, []);

  const handleEnableMockData = useCallback(() => {
    mockDataProvider.setEnabled(true);
    fetchStats();
  }, [fetchStats]);

  // Check if all metrics are zero (empty state) - memoized to prevent recalculation
  // IMPORTANT: All hooks must be called before any early returns
  const isEmpty = useMemo(() => 
    stats && 
    stats.total_leads === 0 && 
    stats.active_jobs === 0 && 
    stats.available_technicians === 0,
    [stats]
  );

  // Memoize stat cards to prevent recreation on every render
  // IMPORTANT: All hooks must be called before any early returns
  const statCards = useMemo(() => [
    { name: 'Total Leads', value: stats?.total_leads || 0, icon: Users, color: 'blue' },
    { name: 'Active Jobs', value: stats?.active_jobs || 0, icon: Briefcase, color: 'green' },
    { name: 'Available Technicians', value: stats?.available_technicians || 0, icon: UserCheck, color: 'purple' },
    { name: 'Completion Rate', value: `${stats?.completion_rate || 0}%`, icon: TrendingUp, color: 'yellow' },
  ], [stats]);

  // Show loading skeleton during data fetch
  if (loading) {
    return (
      <div role="status" aria-live="polite" aria-label="Loading dashboard data">
        <DashboardSkeleton />
      </div>
    );
  }

  // Show empty state when all metrics are zero
  if (isEmpty) {
    return (
      <div className="fade-in" role="region" aria-label="Dashboard empty state">
        <h1 className="font-semibold text-gray-900 mb-6" style={{ fontSize: 'var(--text-2xl)' }}>
          Dashboard
        </h1>
        <div 
          className="text-center py-12 bg-white rounded-lg"
          style={{
            borderRadius: 'var(--radius-lg)',
            boxShadow: 'var(--shadow-sm)',
          }}
        >
          <Database className="mx-auto h-12 w-12 text-gray-400" aria-hidden="true" />
          <h3 className="mt-2 font-medium text-gray-900" style={{ fontSize: 'var(--text-sm)' }}>
            No data available
          </h3>
          <p className="mt-1 text-gray-500" style={{ fontSize: 'var(--text-sm)' }}>
            Get started by adding leads, jobs, and technicians.
          </p>
          <div className="mt-6">
            <button
              onClick={handleEnableMockData}
              className="inline-flex items-center px-4 py-2 border border-transparent font-medium rounded-md text-white transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              style={{
                backgroundColor: 'var(--color-primary-600)',
                boxShadow: 'var(--shadow-sm)',
                fontSize: 'var(--text-sm)',
                borderRadius: 'var(--radius-md)',
                transitionDuration: 'var(--transition-base)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--color-primary-700)';
                e.currentTarget.style.boxShadow = 'var(--shadow-md)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--color-primary-600)';
                e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
              }}
              aria-label="Enable demo data to view sample dashboard"
            >
              View Demo Data
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fade-in" role="region" aria-label="Dashboard statistics">
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-semibold text-gray-900" style={{ fontSize: 'var(--text-2xl)' }}>
          Dashboard
        </h1>
        {usingMockData && (
          <span 
            className="inline-flex items-center px-3 py-1 rounded-full font-medium"
            style={{
              backgroundColor: 'var(--color-primary-100)',
              color: 'var(--color-primary-800)',
              fontSize: 'var(--text-sm)',
              borderRadius: 'var(--radius-full)',
            }}
            role="status"
            aria-label="Currently displaying demo data"
          >
            Demo Data
          </span>
        )}
      </div>
      <ResponsiveGrid>
        {statCards.map((stat) => (
          <StatCard key={stat.name} stat={stat} />
        ))}
      </ResponsiveGrid>
    </div>
  );
}

// Memoized StatCard component to prevent unnecessary re-renders
interface StatCardProps {
  stat: {
    name: string;
    value: number | string;
    icon: React.ComponentType<{ className?: string; 'aria-hidden'?: boolean }>;
    color: string;
  };
}

const StatCard = memo(({ stat }: StatCardProps) => {
  const Icon = stat.icon;
  return (
    <div 
      className="bg-white overflow-hidden"
      style={{
        borderRadius: 'var(--radius-lg)',
        boxShadow: 'var(--shadow-sm)',
      }}
      role="article"
      aria-label={`${stat.name}: ${stat.value}`}
    >
      <div className="p-5">
        <div className="flex items-center">
          <div 
            className={`flex-shrink-0 rounded-md p-3`}
            style={{
              backgroundColor: `var(--color-${stat.color}-500)`,
              borderRadius: 'var(--radius-md)',
            }}
            aria-hidden="true"
          >
            <Icon className="h-6 w-6 text-white" aria-hidden="true" />
          </div>
          <div className="ml-5 w-0 flex-1">
            <dl>
              <dt 
                className="font-medium text-gray-500 truncate"
                style={{ fontSize: 'var(--text-sm)' }}
              >
                {stat.name}
              </dt>
              <dd 
                className="font-semibold text-gray-900"
                style={{ fontSize: 'var(--text-lg)' }}
              >
                {stat.value}
              </dd>
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
});
