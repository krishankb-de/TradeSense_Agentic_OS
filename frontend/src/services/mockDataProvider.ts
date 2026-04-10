/**
 * Mock Data Provider Service
 * Provides realistic sample data for demonstration purposes
 */

import { faker } from '@faker-js/faker';
import { MockDataProvider, Lead, Job, Technician, STORAGE_KEYS } from './types';

class MockDataProviderImpl implements MockDataProvider {
  private seed = 12345; // Consistent seed for reproducible data

  constructor() {
    faker.seed(this.seed);
  }

  isEnabled(): boolean {
    return localStorage.getItem(STORAGE_KEYS.MOCK_DATA_ENABLED) === 'true';
  }

  setEnabled(enabled: boolean): void {
    localStorage.setItem(STORAGE_KEYS.MOCK_DATA_ENABLED, enabled.toString());
  }

  generateLeads(count: number): Lead[] {
    const leads: Lead[] = [];
    const statuses: Lead['status'][] = ['new', 'contacted', 'qualified', 'converted'];
    const sources = ['Website', 'Referral', 'Phone', 'Email', 'Social Media'];

    for (let i = 0; i < count; i++) {
      leads.push({
        id: faker.string.uuid(),
        name: faker.person.fullName(),
        email: faker.internet.email(),
        phone: faker.phone.number(),
        status: faker.helpers.arrayElement(statuses),
        source: faker.helpers.arrayElement(sources),
        created_at: faker.date.recent({ days: 30 }).toISOString(),
      });
    }

    return leads;
  }

  generateJobs(count: number): Job[] {
    const jobs: Job[] = [];
    const statuses: Job['status'][] = ['pending', 'active', 'completed', 'cancelled'];
    const titles = [
      'HVAC Repair',
      'Electrical Installation',
      'Plumbing Fix',
      'Appliance Repair',
      'System Maintenance',
      'Emergency Service',
    ];

    for (let i = 0; i < count; i++) {
      const status = faker.helpers.arrayElement(statuses);
      jobs.push({
        id: faker.string.uuid(),
        title: faker.helpers.arrayElement(titles),
        description: faker.lorem.sentence(),
        status,
        technician_id: status !== 'pending' ? faker.string.uuid() : null,
        lead_id: faker.string.uuid(),
        scheduled_date: faker.date.future({ years: 0.1 }).toISOString(),
        completion_date: status === 'completed' ? faker.date.recent({ days: 7 }).toISOString() : null,
      });
    }

    return jobs;
  }

  generateTechnicians(count: number): Technician[] {
    const technicians: Technician[] = [];
    const skillSets = [
      ['HVAC', 'Electrical'],
      ['Plumbing', 'General Repair'],
      ['Electrical', 'Appliance Repair'],
      ['HVAC', 'Plumbing', 'Electrical'],
      ['General Repair', 'Maintenance'],
    ];

    for (let i = 0; i < count; i++) {
      technicians.push({
        id: faker.string.uuid(),
        name: faker.person.fullName(),
        email: faker.internet.email(),
        phone: faker.phone.number(),
        skills: faker.helpers.arrayElement(skillSets),
        available: faker.datatype.boolean(),
        rating: parseFloat(faker.number.float({ min: 3.5, max: 5.0, fractionDigits: 1 }).toFixed(1)),
      });
    }

    return technicians;
  }

  shouldUseMockData(realData: any[]): boolean {
    return this.isEnabled() && (!realData || realData.length === 0);
  }
}

// Export singleton instance
export const mockDataProvider = new MockDataProviderImpl();
