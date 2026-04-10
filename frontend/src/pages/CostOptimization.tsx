import { useEffect, useState } from 'react';
import api from '../services/api';
import { DollarSign, TrendingDown, AlertCircle } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface CostData {
  total_cost: number;
  budget_remaining: number;
  cost_by_provider: Record<string, number>;
  daily_costs: Array<{ date: string; cost: number }>;
  alerts: Array<{ message: string; severity: string }>;
}

export default function CostOptimization() {
  const [costData, setCostData] = useState<CostData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCostData();
  }, []);

  const fetchCostData = async () => {
    try {
      const response = await api.get('/cost-optimization/dashboard');
      setCostData(response.data);
    } catch (error) {
      console.error('Failed to fetch cost data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-center py-12">Loading...</div>;
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900 mb-6">Cost Optimization</h1>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-3 mb-6">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0 bg-blue-500 rounded-md p-3">
                <DollarSign className="h-6 w-6 text-white" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Total Cost</dt>
                  <dd className="text-lg font-semibold text-gray-900">${costData?.total_cost.toFixed(2)}</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0 bg-green-500 rounded-md p-3">
                <TrendingDown className="h-6 w-6 text-white" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Budget Remaining</dt>
                  <dd className="text-lg font-semibold text-gray-900">${costData?.budget_remaining.toFixed(2)}</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0 bg-yellow-500 rounded-md p-3">
                <AlertCircle className="h-6 w-6 text-white" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Active Alerts</dt>
                  <dd className="text-lg font-semibold text-gray-900">{costData?.alerts.length || 0}</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Cost Trend</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={costData?.daily_costs || []}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="cost" stroke="#3b82f6" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Cost by Provider</h2>
          <div className="space-y-3">
            {Object.entries(costData?.cost_by_provider || {}).map(([provider, cost]) => (
              <div key={provider} className="flex items-center justify-between">
                <span className="text-sm text-gray-600">{provider}</span>
                <span className="text-sm font-medium text-gray-900">${cost.toFixed(2)}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Alerts</h2>
          <div className="space-y-3">
            {costData?.alerts.map((alert, idx) => (
              <div key={idx} className={`p-3 rounded-md ${
                alert.severity === 'high' ? 'bg-red-50 text-red-800' :
                alert.severity === 'medium' ? 'bg-yellow-50 text-yellow-800' :
                'bg-blue-50 text-blue-800'
              }`}>
                <p className="text-sm">{alert.message}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
