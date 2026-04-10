/**
 * Property-based test generators for TradeSense domain models (TypeScript).
 *
 * This module provides fast-check arbitraries for generating valid instances
 * of all domain models used in the TradeSense system. These generators are
 * used by property-based tests to verify correctness properties across
 * 1000+ randomly generated inputs.
 *
 * Usage:
 *   import { leadArb, jobArb, customerArb } from './propertyGenerators';
 *   import fc from 'fast-check';
 *
 *   it('should satisfy lead property', () => {
 *     fc.assert(
 *       fc.property(leadArb, (lead) => {
 *         expect(['emergency', 'urgent', 'routine']).toContain(lead.urgency);
 *       })
 *     );
 *   });
 */

import fc from 'fast-check';
import {
  Availability,
  CarbonFootprint,
  Complexity,
  ComplianceStatus,
  ConversationContext,
  ConversationTurn,
  Diagnosis,
  Entity,
  EquipmentInfo,
  GeoLocation,
  Intent,
  Job,
  JobAssignment,
  JobStatus,
  Lead,
  LeadSource,
  LeadStatus,
  MCPError,
  MCPToolCall,
  Part,
  PartSource,
  PartsRecommendation,
  Route,
  Schedule,
  TriageResult,
  Urgency,
  UserRole,
} from '../types/shared';

// ============================================================================
// Primitive Arbitraries
// ============================================================================

/**
 * Generate valid UUID strings.
 */
export const uuidArb = fc.uuid();

/**
 * Generate recent datetime values (within last 30 days).
 */
export const recentDateArb = fc
  .integer({ min: 0, max: 30 })
  .map((daysAgo) => {
    const date = new Date();
    date.setDate(date.getDate() - daysAgo);
    return date;
  });

/**
 * Generate future datetime values (within next 30 days).
 */
export const futureDateArb = fc
  .integer({ min: 0, max: 30 })
  .map((daysAhead) => {
    const date = new Date();
    date.setDate(date.getDate() + daysAhead);
    return date;
  });

/**
 * Generate valid email addresses.
 */
export const emailArb = fc
  .tuple(
    fc.string({ minLength: 3, maxLength: 20 }).map(s => s.toLowerCase().replace(/[^a-z0-9]/g, '')),
    fc.string({ minLength: 3, maxLength: 15 }).map(s => s.toLowerCase().replace(/[^a-z]/g, '')),
    fc.constantFrom('com', 'org', 'net', 'io', 'dev')
  )
  .map(([username, domain, tld]) => `${username}@${domain}.${tld}`);

/**
 * Generate valid phone numbers.
 */
export const phoneArb = fc
  .tuple(
    fc.integer({ min: 200, max: 999 }),
    fc.integer({ min: 200, max: 999 }),
    fc.integer({ min: 1000, max: 9999 })
  )
  .map(([area, exchange, number]) => `+1-${area}-${exchange}-${number}`);

// ============================================================================
// Base Model Arbitraries
// ============================================================================

/**
 * Generate valid GeoLocation instances.
 */
export const geoLocationArb: fc.Arbitrary<GeoLocation> = fc.record({
  latitude: fc.double({ min: -90, max: 90, noNaN: true }),
  longitude: fc.double({ min: -180, max: 180, noNaN: true }),
  address: fc.string({ minLength: 10, maxLength: 100 }),
  city: fc.string({ minLength: 3, maxLength: 50 }),
  state: fc.constantFrom('CA', 'NY', 'TX', 'FL', 'IL', 'PA', 'OH'),
  zipCode: fc.string({ minLength: 5, maxLength: 5 }).map(s => s.replace(/\D/g, '0').slice(0, 5)),
});

/**
 * Generate valid Part instances.
 */
export const partArb: fc.Arbitrary<Part> = fc.record({
  id: uuidArb,
  name: fc.string({ minLength: 5, maxLength: 50 }),
  manufacturer: fc.constantFrom('Honeywell', 'Carrier', 'Trane', 'Lennox', 'Rheem'),
  modelNumber: fc.string({ minLength: 5, maxLength: 20 }).map(s => s.toUpperCase().replace(/[^A-Z0-9]/g, '')),
  quantity: fc.integer({ min: 1, max: 100 }),
  unitCost: fc.double({ min: 1.0, max: 1000.0, noNaN: true }),
  source: fc.constantFrom(PartSource.INVENTORY, PartSource.ORDERED, PartSource.CUSTOMER_SUPPLIED),
});

// ============================================================================
// Lead Model Arbitraries
// ============================================================================

/**
 * Generate valid Lead instances.
 */
export const leadArb: fc.Arbitrary<Lead> = fc
  .tuple(recentDateArb, fc.integer({ min: 0, max: 48 }))
  .chain(([created, hoursLater]) => {
    const updated = new Date(created);
    updated.setHours(updated.getHours() + hoursLater);

    return fc.record({
      id: uuidArb,
      customerId: uuidArb,
      source: fc.constantFrom(LeadSource.VOICE, LeadSource.SMS, LeadSource.WEB),
      status: fc.constantFrom(
        LeadStatus.NEW,
        LeadStatus.TRIAGED,
        LeadStatus.SCHEDULED,
        LeadStatus.COMPLETED,
        LeadStatus.CANCELLED
      ),
      issueDescription: fc.string({ minLength: 20, maxLength: 500 }),
      urgency: fc.constantFrom(Urgency.EMERGENCY, Urgency.URGENT, Urgency.ROUTINE),
      serviceType: fc.constantFrom('HVAC', 'Plumbing', 'Electrical', 'Appliance Repair'),
      location: geoLocationArb,
      createdAt: fc.constant(created),
      updatedAt: fc.constant(updated),
      assignedTechnicianId: fc.option(uuidArb, { nil: undefined }),
      estimatedValue: fc.double({ min: 50.0, max: 5000.0, noNaN: true }),
    });
  });

/**
 * Generate valid TriageResult instances.
 */
export const triageResultArb: fc.Arbitrary<TriageResult> = fc.record({
  serviceType: fc.constantFrom('HVAC', 'Plumbing', 'Electrical', 'Appliance Repair'),
  estimatedDuration: fc.integer({ min: 30, max: 480 }),
  requiredSkills: fc.array(fc.constantFrom('HVAC', 'Electrical', 'Plumbing', 'Diagnostics'), { minLength: 1, maxLength: 3 }),
  suggestedTechnicians: fc.array(uuidArb, { minLength: 1, maxLength: 5 }),
  priority: fc.integer({ min: 1, max: 10 }),
  confidence: fc.double({ min: 0.0, max: 1.0, noNaN: true }),
});

// ============================================================================
// Job Model Arbitraries
// ============================================================================

/**
 * Generate valid Diagnosis instances.
 */
export const diagnosisArb: fc.Arbitrary<Diagnosis> = fc.record({
  issueType: fc.constantFrom('Compressor Failure', 'Refrigerant Leak', 'Thermostat Malfunction', 'Electrical Issue'),
  rootCause: fc.string({ minLength: 20, maxLength: 200 }),
  confidence: fc.double({ min: 0.0, max: 1.0, noNaN: true }),
  requiredParts: fc.array(partArb, { minLength: 0, maxLength: 5 }),
  estimatedRepairTime: fc.integer({ min: 30, max: 480 }),
  complexity: fc.constantFrom(Complexity.SIMPLE, Complexity.MODERATE, Complexity.COMPLEX),
  reasoningSteps: fc.array(fc.string({ minLength: 10, maxLength: 100 }), { minLength: 0, maxLength: 5 }),
});

/**
 * Generate valid CarbonFootprint instances.
 */
export const carbonFootprintArb: fc.Arbitrary<CarbonFootprint> = fc
  .tuple(fc.double({ min: 0.0, max: 50.0, noNaN: true }), fc.double({ min: 0.0, max: 30.0, noNaN: true }))
  .chain(([travelEmissions, partsEmissions]) =>
    fc.record({
      totalEmissions: fc.constant(travelEmissions + partsEmissions),
      breakdown: fc.constant([
        { category: 'travel', emissions: travelEmissions },
        { category: 'parts', emissions: partsEmissions },
      ]),
      complianceStatus: fc.constantFrom(ComplianceStatus.COMPLIANT, ComplianceStatus.WARNING, ComplianceStatus.NON_COMPLIANT),
      recommendations: fc.array(fc.string({ minLength: 10, maxLength: 100 }), { minLength: 0, maxLength: 3 }),
      dataSources: fc.array(fc.constantFrom('eGRID', 'EPA-GHG', 'ADEME', 'Kabaun'), { minLength: 1, maxLength: 4 }),
    })
  );

/**
 * Generate valid Job instances.
 */
export const jobArb: fc.Arbitrary<Job> = fc
  .tuple(futureDateArb, fc.integer({ min: 1, max: 8 }), fc.boolean())
  .chain(([scheduledStart, durationHours, hasActualTimes]) => {
    const scheduledEnd = new Date(scheduledStart);
    scheduledEnd.setHours(scheduledEnd.getHours() + durationHours);

    let actualStart: Date | undefined;
    let actualEnd: Date | undefined;

    if (hasActualTimes) {
      actualStart = new Date(scheduledStart);
      actualStart.setMinutes(actualStart.getMinutes() + Math.floor(Math.random() * 60 - 30));
      actualEnd = new Date(actualStart);
      actualEnd.setHours(actualEnd.getHours() + durationHours);
    }

    return fc.record({
      id: uuidArb,
      leadId: uuidArb,
      technicianId: uuidArb,
      status: fc.constantFrom(JobStatus.SCHEDULED, JobStatus.IN_PROGRESS, JobStatus.COMPLETED, JobStatus.CANCELLED),
      scheduledStart: fc.constant(scheduledStart),
      scheduledEnd: fc.constant(scheduledEnd),
      actualStart: fc.constant(actualStart),
      actualEnd: fc.constant(actualEnd),
      diagnosis: fc.option(diagnosisArb, { nil: undefined }),
      partsUsed: fc.array(partArb, { minLength: 0, maxLength: 5 }),
      laborHours: fc.double({ min: 0.5, max: 8.0, noNaN: true }),
      totalCost: fc.double({ min: 50.0, max: 5000.0, noNaN: true }),
      customerSignature: fc.option(fc.string({ minLength: 10, maxLength: 100 }), { nil: undefined }),
      photos: fc.array(fc.string({ minLength: 10, maxLength: 100 }), { minLength: 0, maxLength: 10 }),
      notes: fc.string({ minLength: 0, maxLength: 500 }),
      carbonFootprint: fc.option(carbonFootprintArb, { nil: undefined }),
    });
  });

// ============================================================================
// Conversation Model Arbitraries
// ============================================================================

/**
 * Generate valid Intent instances.
 */
export const intentArb: fc.Arbitrary<Intent> = fc.record({
  name: fc.constantFrom('JOB_COMPLETION', 'LEAD_INTAKE', 'DIAGNOSIS', 'PARTS_QUERY', 'SCHEDULING'),
  confidence: fc.double({ min: 0.0, max: 1.0, noNaN: true }),
  parameters: fc.dictionary(fc.string({ minLength: 1, maxLength: 20 }), fc.string({ minLength: 1, maxLength: 50 })),
});

/**
 * Generate valid Entity instances.
 */
export const entityArb: fc.Arbitrary<Entity> = fc
  .tuple(fc.integer({ min: 0, max: 100 }), fc.integer({ min: 1, max: 50 }))
  .chain(([start, length]) =>
    fc.record({
      type: fc.constantFrom('PART_NUMBER', 'TECHNICIAN_NAME', 'CUSTOMER_NAME', 'DATE', 'TIME'),
      value: fc.string({ minLength: 1, maxLength: 50 }),
      confidence: fc.double({ min: 0.0, max: 1.0, noNaN: true }),
      span: fc.constant<[number, number]>([start, start + length]),
    })
  );

/**
 * Generate valid ConversationTurn instances.
 */
export const conversationTurnArb: fc.Arbitrary<ConversationTurn> = fc.record({
  speaker: fc.constantFrom('user', 'agent'),
  content: fc.string({ minLength: 10, maxLength: 500 }),
  timestamp: recentDateArb,
  agent: fc.option(fc.constantFrom('intake', 'diagnostic', 'fulfillment'), { nil: undefined }),
  actions: fc.array(fc.dictionary(fc.string({ minLength: 1, maxLength: 20 }), fc.string({ minLength: 1, maxLength: 50 })), {
    minLength: 0,
    maxLength: 3,
  }),
});

/**
 * Generate valid ConversationContext instances.
 */
export const conversationContextArb: fc.Arbitrary<ConversationContext> = fc
  .tuple(recentDateArb, fc.integer({ min: 0, max: 10 }))
  .chain(([startTime, historyLength]) => {
    // Generate chronologically ordered history
    const historyArb = fc.array(
      fc.record({
        speaker: fc.constantFrom('user', 'agent'),
        content: fc.string({ minLength: 10, maxLength: 500 }),
        agent: fc.option(fc.constantFrom('intake', 'diagnostic', 'fulfillment'), { nil: undefined }),
        actions: fc.array(fc.dictionary(fc.string({ minLength: 1, maxLength: 20 }), fc.string({ minLength: 1, maxLength: 50 })), {
          minLength: 0,
          maxLength: 3,
        }),
      }),
      { minLength: 0, maxLength: historyLength }
    ).map((turns) => {
      // Add chronologically ordered timestamps
      return turns.map((turn, index) => {
        const timestamp = new Date(startTime);
        timestamp.setMinutes(timestamp.getMinutes() + index);
        return { ...turn, timestamp };
      });
    });

    return fc.record({
      sessionId: uuidArb,
      userId: uuidArb,
      userRole: fc.constantFrom(UserRole.TECHNICIAN, UserRole.CUSTOMER, UserRole.DISPATCHER, UserRole.ADMIN),
      currentIntent: fc.option(intentArb, { nil: undefined }),
      entities: fc.array(entityArb, { minLength: 0, maxLength: 5 }),
      history: historyArb,
      state: fc.dictionary(fc.string({ minLength: 1, maxLength: 20 }), fc.string({ minLength: 1, maxLength: 50 })),
      metadata: fc.constant({
        startTime: startTime.getTime(),
        turnCount: historyLength,
        activeAgents: ['intake', 'diagnostic', 'fulfillment'].slice(0, Math.floor(Math.random() * 4)),
      }),
    });
  });

// ============================================================================
// MCP Model Arbitraries
// ============================================================================

/**
 * Generate valid MCPError instances.
 */
export const mcpErrorArb: fc.Arbitrary<MCPError> = fc.record({
  code: fc.integer({ min: -32768, max: -32000 }),
  message: fc.string({ minLength: 10, maxLength: 200 }),
  data: fc.option(fc.dictionary(fc.string({ minLength: 1, maxLength: 20 }), fc.string({ minLength: 1, maxLength: 50 })), {
    nil: undefined,
  }),
});

/**
 * Generate valid MCPToolCall instances.
 */
export const mcpToolCallArb: fc.Arbitrary<MCPToolCall> = fc.record({
  id: uuidArb,
  serverId: fc.constantFrom('filesystem', 'database', 'inventree', 'partdb', 'kicost'),
  toolName: fc.string({ minLength: 5, maxLength: 50 }),
  parameters: fc.dictionary(fc.string({ minLength: 1, maxLength: 20 }), fc.string({ minLength: 1, maxLength: 50 })),
  result: fc.option(fc.string({ minLength: 10, maxLength: 200 }), { nil: undefined }),
  error: fc.option(mcpErrorArb, { nil: undefined }),
  timestamp: recentDateArb,
  duration: fc.integer({ min: 10, max: 5000 }),
  agentId: fc.constantFrom('intake', 'diagnostic', 'fulfillment'),
});

// ============================================================================
// Parts and Inventory Model Arbitraries
// ============================================================================

/**
 * Generate valid PartsRecommendation instances.
 */
export const partsRecommendationArb: fc.Arbitrary<PartsRecommendation> = fc
  .array(partArb, { minLength: 1, maxLength: 3 })
  .chain((primaryParts) => {
    const totalCost = primaryParts.reduce((sum, p) => sum + p.unitCost * p.quantity, 0);

    return fc.record({
      primary: fc.constant(primaryParts),
      alternatives: fc.array(fc.array(partArb, { minLength: 1, maxLength: 3 }), { minLength: 0, maxLength: 3 }),
      totalCost: fc.constant(totalCost),
      availability: fc.constantFrom(Availability.IN_STOCK, Availability.ORDER_REQUIRED, Availability.UNAVAILABLE),
      distributorOptions: fc.array(
        fc.record({
          distributor: fc.constantFrom('digikey', 'mouser', 'arrow', 'newark', 'tme'),
          price: fc.double({ min: 1.0, max: 1000.0, noNaN: true }),
          leadTime: fc.integer({ min: 0, max: 30 }),
          quantity: fc.integer({ min: 1, max: 100 }),
        }),
        { minLength: 0, maxLength: 5 }
      ),
    });
  });

/**
 * Generate valid EquipmentInfo instances.
 */
export const equipmentInfoArb: fc.Arbitrary<EquipmentInfo> = fc.record({
  manufacturer: fc.constantFrom('Honeywell', 'Carrier', 'Trane', 'Lennox', 'Rheem'),
  model: fc.string({ minLength: 5, maxLength: 20 }).map(s => s.toUpperCase().replace(/[^A-Z0-9]/g, '')),
  serialNumber: fc.option(fc.string({ minLength: 8, maxLength: 20 }).map(s => s.toUpperCase().replace(/[^A-Z0-9]/g, '')), {
    nil: undefined,
  }),
  type: fc.constantFrom('Air Conditioner', 'Furnace', 'Heat Pump', 'Thermostat'),
  specifications: fc.dictionary(fc.string({ minLength: 1, maxLength: 20 }), fc.string({ minLength: 1, maxLength: 50 })),
});

// ============================================================================
// Schedule Model Arbitraries
// ============================================================================

/**
 * Generate valid JobAssignment instances.
 */
export const jobAssignmentArb: fc.Arbitrary<JobAssignment> = fc
  .tuple(futureDateArb, fc.integer({ min: 1, max: 8 }))
  .chain(([scheduledStart, durationHours]) => {
    const scheduledEnd = new Date(scheduledStart);
    scheduledEnd.setHours(scheduledEnd.getHours() + durationHours);

    return fc.record({
      jobId: uuidArb,
      technicianId: uuidArb,
      scheduledStart: fc.constant(scheduledStart),
      scheduledEnd: fc.constant(scheduledEnd),
      estimatedTravelTime: fc.integer({ min: 0, max: 120 }),
    });
  });

/**
 * Generate valid Route instances.
 */
export const routeArb: fc.Arbitrary<Route> = fc
  .array(jobAssignmentArb, { minLength: 1, maxLength: 10 })
  .chain((assignments) =>
    fc.record({
      technicianId: uuidArb,
      assignments: fc.constant(assignments),
      totalDistance: fc.double({ min: 0.0, max: 500.0, noNaN: true }),
      totalDuration: fc.integer({ min: 60, max: 600 }),
    })
  );

/**
 * Generate valid Schedule instances.
 */
export const scheduleArb: fc.Arbitrary<Schedule> = fc
  .tuple(fc.array(jobAssignmentArb, { minLength: 1, maxLength: 20 }), fc.array(routeArb, { minLength: 1, maxLength: 5 }))
  .chain(([assignments, routes]) =>
    fc.record({
      assignments: fc.constant(assignments),
      routes: fc.constant(routes),
      estimatedCompletionTime: fc.integer({ min: 60, max: 600 }),
      utilizationRate: fc.double({ min: 0.0, max: 1.0, noNaN: true }),
    })
  );

// ============================================================================
// Mock Data Provider Arbitraries (Frontend)
// ============================================================================

/**
 * Generate valid Lead instances for frontend mock data.
 * Note: This is different from the backend Lead type.
 */
export const mockLeadArb: fc.Arbitrary<{
  id: string;
  name: string;
  email: string;
  phone: string;
  status: 'new' | 'contacted' | 'qualified' | 'converted';
  source: string;
  created_at: string;
}> = fc.record({
  id: uuidArb,
  name: fc.string({ minLength: 3, maxLength: 50 }),
  email: emailArb,
  phone: phoneArb,
  status: fc.constantFrom('new', 'contacted', 'qualified', 'converted'),
  source: fc.constantFrom('Website', 'Referral', 'Phone', 'Email', 'Social Media'),
  created_at: recentDateArb.map(d => d.toISOString()),
});

/**
 * Generate valid Job instances for frontend mock data.
 * Note: This is different from the backend Job type.
 */
export const mockJobArb: fc.Arbitrary<{
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'active' | 'completed' | 'cancelled';
  technician_id: string | null;
  lead_id: string;
  scheduled_date: string;
  completion_date: string | null;
}> = fc
  .tuple(
    fc.constantFrom('pending', 'active', 'completed', 'cancelled'),
    futureDateArb,
    fc.option(recentDateArb, { nil: null })
  )
  .chain(([status, scheduledDate, completionDate]) =>
    fc.record({
      id: uuidArb,
      title: fc.constantFrom(
        'HVAC Repair',
        'Electrical Installation',
        'Plumbing Fix',
        'Appliance Repair',
        'System Maintenance',
        'Emergency Service'
      ),
      description: fc.string({ minLength: 10, maxLength: 200 }),
      status: fc.constant(status),
      technician_id: status === 'pending' ? fc.constant(null) : fc.option(uuidArb, { nil: null }),
      lead_id: uuidArb,
      scheduled_date: fc.constant(scheduledDate.toISOString()),
      completion_date: status === 'completed' && completionDate ? fc.constant(completionDate.toISOString()) : fc.constant(null),
    })
  );

/**
 * Generate valid Technician instances for frontend mock data.
 */
export const mockTechnicianArb: fc.Arbitrary<{
  id: string;
  name: string;
  email: string;
  phone: string;
  skills: string[];
  available: boolean;
  rating: number;
}> = fc.record({
  id: uuidArb,
  name: fc.string({ minLength: 3, maxLength: 50 }),
  email: emailArb,
  phone: phoneArb,
  skills: fc.array(
    fc.constantFrom('HVAC', 'Electrical', 'Plumbing', 'General Repair', 'Appliance Repair', 'Maintenance'),
    { minLength: 1, maxLength: 4 }
  ),
  available: fc.boolean(),
  rating: fc.double({ min: 3.5, max: 5.0, noNaN: true }).map(r => parseFloat(r.toFixed(1))),
});
