/**
 * Unit tests for Mock Data Provider Service
 * 
 * **Validates: Requirements 4.4, 12.1, 12.2, 12.3, 12.4, 12.6**
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mockDataProvider } from '../mockDataProvider';
import { STORAGE_KEYS } from '../types';

describe('MockDataProvider - Unit Tests', () => {
  // Store original localStorage state
  let originalLocalStorage: Storage;

  beforeEach(() => {
    // Save original localStorage
    originalLocalStorage = { ...localStorage };
    // Clear localStorage before each test
    localStorage.clear();
  });

  afterEach(() => {
    // Restore original localStorage
    Object.keys(originalLocalStorage).forEach(key => {
      localStorage.setItem(key, originalLocalStorage[key]);
    });
  });

  describe('Enable/Disable Toggle', () => {
    it('should be disabled by default', () => {
      expect(mockDataProvider.isEnabled()).toBe(false);
    });

    it('should enable mock data when setEnabled(true) is called', () => {
      mockDataProvider.setEnabled(true);
      expect(mockDataProvider.isEnabled()).toBe(true);
      expect(localStorage.getItem(STORAGE_KEYS.MOCK_DATA_ENABLED)).toBe('true');
    });

    it('should disable mock data when setEnabled(false) is called', () => {
      mockDataProvider.setEnabled(true);
      expect(mockDataProvider.isEnabled()).toBe(true);

      mockDataProvider.setEnabled(false);
      expect(mockDataProvider.isEnabled()).toBe(false);
      expect(localStorage.getItem(STORAGE_KEYS.MOCK_DATA_ENABLED)).toBe('false');
    });

    it('should persist enabled state across instances', () => {
      mockDataProvider.setEnabled(true);
      
      // Simulate reading from localStorage (as a new instance would)
      const storedValue = localStorage.getItem(STORAGE_KEYS.MOCK_DATA_ENABLED);
      expect(storedValue).toBe('true');
      
      // Verify isEnabled reads from localStorage
      expect(mockDataProvider.isEnabled()).toBe(true);
    });

    it('should toggle state multiple times correctly', () => {
      expect(mockDataProvider.isEnabled()).toBe(false);

      mockDataProvider.setEnabled(true);
      expect(mockDataProvider.isEnabled()).toBe(true);

      mockDataProvider.setEnabled(false);
      expect(mockDataProvider.isEnabled()).toBe(false);

      mockDataProvider.setEnabled(true);
      expect(mockDataProvider.isEnabled()).toBe(true);
    });
  });

  describe('shouldUseMockData Logic', () => {
    it('should return true when enabled and data is empty array', () => {
      mockDataProvider.setEnabled(true);
      expect(mockDataProvider.shouldUseMockData([])).toBe(true);
    });

    it('should return true when enabled and data is null', () => {
      mockDataProvider.setEnabled(true);
      expect(mockDataProvider.shouldUseMockData(null as any)).toBe(true);
    });

    it('should return true when enabled and data is undefined', () => {
      mockDataProvider.setEnabled(true);
      expect(mockDataProvider.shouldUseMockData(undefined as any)).toBe(true);
    });

    it('should return false when disabled and data is empty', () => {
      mockDataProvider.setEnabled(false);
      expect(mockDataProvider.shouldUseMockData([])).toBe(false);
    });

    it('should return false when enabled but data exists', () => {
      mockDataProvider.setEnabled(true);
      expect(mockDataProvider.shouldUseMockData([{ id: 1 }])).toBe(false);
      expect(mockDataProvider.shouldUseMockData([1, 2, 3])).toBe(false);
    });

    it('should return false when disabled and data exists', () => {
      mockDataProvider.setEnabled(false);
      expect(mockDataProvider.shouldUseMockData([{ id: 1 }])).toBe(false);
    });
  });

  describe('generateLeads', () => {
    it('should generate the requested number of leads', () => {
      const leads = mockDataProvider.generateLeads(5);
      expect(leads).toHaveLength(5);
    });

    it('should generate zero leads when count is 0', () => {
      const leads = mockDataProvider.generateLeads(0);
      expect(leads).toHaveLength(0);
    });

    it('should generate leads with all required fields', () => {
      const leads = mockDataProvider.generateLeads(1);
      const lead = leads[0];

      expect(lead).toHaveProperty('id');
      expect(lead).toHaveProperty('name');
      expect(lead).toHaveProperty('email');
      expect(lead).toHaveProperty('phone');
      expect(lead).toHaveProperty('status');
      expect(lead).toHaveProperty('source');
      expect(lead).toHaveProperty('created_at');
    });

    it('should generate leads with valid status values', () => {
      const leads = mockDataProvider.generateLeads(10);
      const validStatuses = ['new', 'contacted', 'qualified', 'converted'];

      leads.forEach(lead => {
        expect(validStatuses).toContain(lead.status);
      });
    });

    it('should generate leads with valid email format', () => {
      const leads = mockDataProvider.generateLeads(10);
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

      leads.forEach(lead => {
        expect(lead.email).toMatch(emailRegex);
      });
    });

    it('should generate leads with valid ISO date strings', () => {
      const leads = mockDataProvider.generateLeads(10);

      leads.forEach(lead => {
        expect(() => new Date(lead.created_at)).not.toThrow();
        expect(new Date(lead.created_at).toISOString()).toBe(lead.created_at);
      });
    });
  });

  describe('generateJobs', () => {
    it('should generate the requested number of jobs', () => {
      const jobs = mockDataProvider.generateJobs(5);
      expect(jobs).toHaveLength(5);
    });

    it('should generate zero jobs when count is 0', () => {
      const jobs = mockDataProvider.generateJobs(0);
      expect(jobs).toHaveLength(0);
    });

    it('should generate jobs with all required fields', () => {
      const jobs = mockDataProvider.generateJobs(1);
      const job = jobs[0];

      expect(job).toHaveProperty('id');
      expect(job).toHaveProperty('title');
      expect(job).toHaveProperty('description');
      expect(job).toHaveProperty('status');
      expect(job).toHaveProperty('technician_id');
      expect(job).toHaveProperty('lead_id');
      expect(job).toHaveProperty('scheduled_date');
      expect(job).toHaveProperty('completion_date');
    });

    it('should generate jobs with valid status values', () => {
      const jobs = mockDataProvider.generateJobs(10);
      const validStatuses = ['pending', 'active', 'completed', 'cancelled'];

      jobs.forEach(job => {
        expect(validStatuses).toContain(job.status);
      });
    });

    it('should not assign technician to pending jobs', () => {
      const jobs = mockDataProvider.generateJobs(20);
      const pendingJobs = jobs.filter(job => job.status === 'pending');

      pendingJobs.forEach(job => {
        expect(job.technician_id).toBeNull();
      });
    });

    it('should assign completion date to completed jobs', () => {
      const jobs = mockDataProvider.generateJobs(20);
      const completedJobs = jobs.filter(job => job.status === 'completed');

      completedJobs.forEach(job => {
        expect(job.completion_date).not.toBeNull();
        expect(() => new Date(job.completion_date!)).not.toThrow();
      });
    });

    it('should generate jobs with valid ISO date strings', () => {
      const jobs = mockDataProvider.generateJobs(10);

      jobs.forEach(job => {
        expect(() => new Date(job.scheduled_date)).not.toThrow();
        expect(new Date(job.scheduled_date).toISOString()).toBe(job.scheduled_date);

        if (job.completion_date) {
          expect(() => new Date(job.completion_date)).not.toThrow();
          expect(new Date(job.completion_date).toISOString()).toBe(job.completion_date);
        }
      });
    });
  });

  describe('generateTechnicians', () => {
    it('should generate the requested number of technicians', () => {
      const technicians = mockDataProvider.generateTechnicians(5);
      expect(technicians).toHaveLength(5);
    });

    it('should generate zero technicians when count is 0', () => {
      const technicians = mockDataProvider.generateTechnicians(0);
      expect(technicians).toHaveLength(0);
    });

    it('should generate technicians with all required fields', () => {
      const technicians = mockDataProvider.generateTechnicians(1);
      const technician = technicians[0];

      expect(technician).toHaveProperty('id');
      expect(technician).toHaveProperty('name');
      expect(technician).toHaveProperty('email');
      expect(technician).toHaveProperty('phone');
      expect(technician).toHaveProperty('skills');
      expect(technician).toHaveProperty('available');
      expect(technician).toHaveProperty('rating');
    });

    it('should generate technicians with valid email format', () => {
      const technicians = mockDataProvider.generateTechnicians(10);
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

      technicians.forEach(technician => {
        expect(technician.email).toMatch(emailRegex);
      });
    });

    it('should generate technicians with non-empty skills array', () => {
      const technicians = mockDataProvider.generateTechnicians(10);

      technicians.forEach(technician => {
        expect(Array.isArray(technician.skills)).toBe(true);
        expect(technician.skills.length).toBeGreaterThan(0);
        technician.skills.forEach(skill => {
          expect(typeof skill).toBe('string');
          expect(skill.length).toBeGreaterThan(0);
        });
      });
    });

    it('should generate technicians with valid rating range', () => {
      const technicians = mockDataProvider.generateTechnicians(10);

      technicians.forEach(technician => {
        expect(technician.rating).toBeGreaterThanOrEqual(0);
        expect(technician.rating).toBeLessThanOrEqual(5);
      });
    });

    it('should generate technicians with boolean available field', () => {
      const technicians = mockDataProvider.generateTechnicians(10);

      technicians.forEach(technician => {
        expect(typeof technician.available).toBe('boolean');
      });
    });
  });

  describe('Data Consistency', () => {
    it('should generate unique IDs for leads', () => {
      const leads = mockDataProvider.generateLeads(50);
      const ids = leads.map(lead => lead.id);
      const uniqueIds = new Set(ids);

      expect(uniqueIds.size).toBe(ids.length);
    });

    it('should generate unique IDs for jobs', () => {
      const jobs = mockDataProvider.generateJobs(50);
      const ids = jobs.map(job => job.id);
      const uniqueIds = new Set(ids);

      expect(uniqueIds.size).toBe(ids.length);
    });

    it('should generate unique IDs for technicians', () => {
      const technicians = mockDataProvider.generateTechnicians(50);
      const ids = technicians.map(tech => tech.id);
      const uniqueIds = new Set(ids);

      expect(uniqueIds.size).toBe(ids.length);
    });
  });
});
