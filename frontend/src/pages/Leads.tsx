import { useEffect, useState, memo } from 'react';
import api from '../services/api';
import { Plus, Phone, Mail, Search } from 'lucide-react';
import { useDebounce } from '../utils/debounce';

interface Lead {
  id: string;
  name: string;
  email: string;
  phone: string;
  status: string;
  created_at: string;
}

// Memoized LeadItem component to prevent unnecessary re-renders
const LeadItem = memo(({ lead }: { lead: Lead }) => (
  <li key={lead.id}>
    <div className="px-4 py-4 sm:px-6 hover:bg-gray-50">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-blue-600">{lead.name}</p>
          <div className="mt-2 flex items-center text-sm text-gray-500">
            <Mail className="flex-shrink-0 mr-1.5 h-4 w-4 text-gray-400" />
            {lead.email}
            <Phone className="flex-shrink-0 ml-4 mr-1.5 h-4 w-4 text-gray-400" />
            {lead.phone}
          </div>
        </div>
        <div className="ml-4">
          <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
            lead.status === 'new' ? 'bg-green-100 text-green-800' :
            lead.status === 'contacted' ? 'bg-blue-100 text-blue-800' :
            'bg-gray-100 text-gray-800'
          }`}>
            {lead.status}
          </span>
        </div>
      </div>
    </div>
  </li>
));

export default function Leads() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const debouncedSearchQuery = useDebounce(searchQuery, 300);

  useEffect(() => {
    fetchLeads();
  }, []);

  useEffect(() => {
    // Trigger search when debounced query changes
    if (debouncedSearchQuery !== undefined) {
      fetchLeads(debouncedSearchQuery);
    }
  }, [debouncedSearchQuery]);

  const fetchLeads = async (search?: string) => {
    try {
      const params = search ? { search } : {};
      const response = await api.get('/leads', { params });
      setLeads(response.data);
    } catch (error) {
      console.error('Failed to fetch leads:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-center py-12">Loading...</div>;
  }

  return (
    <div>
      <div className="sm:flex sm:items-center sm:justify-between mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Leads</h1>
        <button className="mt-4 sm:mt-0 inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700">
          <Plus className="w-4 h-4 mr-2" />
          Add Lead
        </button>
      </div>

      {/* Search input with debouncing */}
      <div className="mb-4">
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type="text"
            placeholder="Search leads by name, email, or phone..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
          />
        </div>
      </div>

      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <ul className="divide-y divide-gray-200">
          {leads.map((lead) => (
            <LeadItem key={lead.id} lead={lead} />
          ))}
        </ul>
      </div>
    </div>
  );
}
