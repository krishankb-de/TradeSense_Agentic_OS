import { useEffect, useState, memo } from 'react';
import api from '../services/api';
import { Plus, Phone, Mail, MapPin, Search } from 'lucide-react';
import { useDebounce } from '../utils/debounce';

interface Technician {
  id: string;
  name: string;
  email: string;
  phone: string;
  skills: string[];
  location: string;
  available: boolean;
}

// Memoized TechnicianCard component to prevent unnecessary re-renders
const TechnicianCard = memo(({ tech }: { tech: Technician }) => (
  <div key={tech.id} className="bg-white overflow-hidden shadow rounded-lg">
    <div className="px-4 py-5 sm:p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-gray-900">{tech.name}</h3>
        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
          tech.available ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
        }`}>
          {tech.available ? 'Available' : 'Busy'}
        </span>
      </div>
      <div className="space-y-2 text-sm text-gray-500">
        <div className="flex items-center">
          <Mail className="flex-shrink-0 mr-2 h-4 w-4 text-gray-400" />
          {tech.email}
        </div>
        <div className="flex items-center">
          <Phone className="flex-shrink-0 mr-2 h-4 w-4 text-gray-400" />
          {tech.phone}
        </div>
        <div className="flex items-center">
          <MapPin className="flex-shrink-0 mr-2 h-4 w-4 text-gray-400" />
          {tech.location}
        </div>
      </div>
      <div className="mt-4">
        <p className="text-xs text-gray-500 mb-2">Skills:</p>
        <div className="flex flex-wrap gap-1">
          {tech.skills.map((skill, idx) => (
            <span key={idx} className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
              {skill}
            </span>
          ))}
        </div>
      </div>
    </div>
  </div>
));

export default function Technicians() {
  const [technicians, setTechnicians] = useState<Technician[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const debouncedSearchQuery = useDebounce(searchQuery, 300);

  useEffect(() => {
    fetchTechnicians();
  }, []);

  useEffect(() => {
    // Trigger search when debounced query changes
    if (debouncedSearchQuery !== undefined) {
      fetchTechnicians(debouncedSearchQuery);
    }
  }, [debouncedSearchQuery]);

  const fetchTechnicians = async (search?: string) => {
    try {
      const params = search ? { search } : {};
      const response = await api.get('/technicians', { params });
      setTechnicians(response.data);
    } catch (error) {
      console.error('Failed to fetch technicians:', error);
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
        <h1 className="text-2xl font-semibold text-gray-900">Technicians</h1>
        <button className="mt-4 sm:mt-0 inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700">
          <Plus className="w-4 h-4 mr-2" />
          Add Technician
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
            placeholder="Search technicians by name, email, or skills..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {technicians.map((tech) => (
          <TechnicianCard key={tech.id} tech={tech} />
        ))}
      </div>
    </div>
  );
}
