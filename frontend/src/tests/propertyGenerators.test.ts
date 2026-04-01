/**
 * Example property-based tests demonstrating the use of custom generators.
 *
 * This module shows how to use the property generators to write property-based
 * tests for TradeSense domain models. These tests verify invariants and
 * correctness properties across 1000+ randomly generated inputs.
 *
 * Run with:
 *   npm test
 *   TEST_PROFILE=thorough npm test
 */

import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import {
  leadArb,
  jobArb,
  diagnosisArb,
  partArb,
  conversationContextArb,
  scheduleArb,
  mcpToolCallArb,
  triageResultArb,
} from './propertyGenerators';
import { assertProperty, getPropertyTestConfig } from './propertyTestConfig';
import {
  LeadSource,
  LeadStatus,
  Urgency,
  JobStatus,
  PartSource,
  Complexity,
} from '../types/shared';

describe('Lead Properties', () => {
  it('should have valid urgency level', () => {
    assertProperty(leadArb, (lead) => {
      expect([Urgency.EMERGENCY, Urgency.URGENT, Urgency.ROUTINE]).toContain(lead.urgency);
    });
  });

  it('should have valid source', () => {
    assertProperty(leadArb, (lead) => {
      expect([LeadSource.VOICE, LeadSource.SMS, LeadSource.WEB]).toContain(lead.source);
    });
  });

  it('should have valid status', () => {
    assertProperty(leadArb, (lead) => {
      expect([
        LeadStatus.NEW,
        LeadStatus.TRIAGED,
        LeadStatus.SCHEDULED,
        LeadStatus.COMPLETED,
        LeadStatus.CANCELLED,
      ]).toContain(lead.status);
    });
  });

  it('should have updatedAt >= createdAt', () => {
    assertProperty(leadArb, (lead) => {
      expect(lead.updatedAt.getTime()).toBeGreaterThanOrEqual(lead.createdAt.getTime());
    });
  });

  it('should have non-negative estimated value', () => {
    assertProperty(leadArb, (lead) => {
      expect(lead.estimatedValue).toBeGreaterThanOrEqual(0);
    });
  });

  it('should have valid GPS coordinates', () => {
    assertProperty(leadArb, (lead) => {
      expect(lead.location.latitude).toBeGreaterThanOrEqual(-90);
      expect(lead.location.latitude).toBeLessThanOrEqual(90);
      expect(lead.location.longitude).toBeGreaterThanOrEqual(-180);
      expect(lead.location.longitude).toBeLessThanOrEqual(180);
    });
  });
});

describe('Job Properties', () => {
  it('should have scheduledEnd after scheduledStart', () => {
    assertProperty(jobArb, (job) => {
      expect(job.scheduledEnd.getTime()).toBeGreaterThan(job.scheduledStart.getTime());
    });
  });

  it('should have actualEnd after actualStart when both are set', () => {
    assertProperty(jobArb, (job) => {
      if (job.actualStart && job.actualEnd) {
        expect(job.actualEnd.getTime()).toBeGreaterThan(job.actualStart.getTime());
      }
    });
  });

  it('should have non-negative labor hours', () => {
    assertProperty(jobArb, (job) => {
      expect(job.laborHours).toBeGreaterThanOrEqual(0);
    });
  });

  it('should have non-negative total cost', () => {
    assertProperty(jobArb, (job) => {
      expect(job.totalCost).toBeGreaterThanOrEqual(0);
    });
  });

  it('should have parts with positive quantity', () => {
    assertProperty(jobArb, (job) => {
      job.partsUsed.forEach((part) => {
        expect(part.quantity).toBeGreaterThan(0);
      });
    });
  });

  it('should have parts with non-negative unit cost', () => {
    assertProperty(jobArb, (job) => {
      job.partsUsed.forEach((part) => {
        expect(part.unitCost).toBeGreaterThanOrEqual(0);
      });
    });
  });
});

describe('Diagnosis Properties', () => {
  it('should have confidence between 0 and 1', () => {
    assertProperty(diagnosisArb, (diagnosis) => {
      expect(diagnosis.confidence).toBeGreaterThanOrEqual(0);
      expect(diagnosis.confidence).toBeLessThanOrEqual(1);
    });
  });

  it('should have positive estimated repair time', () => {
    assertProperty(diagnosisArb, (diagnosis) => {
      expect(diagnosis.estimatedRepairTime).toBeGreaterThan(0);
    });
  });

  it('should have valid complexity', () => {
    assertProperty(diagnosisArb, (diagnosis) => {
      expect([Complexity.SIMPLE, Complexity.MODERATE, Complexity.COMPLEX]).toContain(diagnosis.complexity);
    });
  });
});

describe('Part Properties', () => {
  it('should have positive quantity', () => {
    assertProperty(partArb, (part) => {
      expect(part.quantity).toBeGreaterThan(0);
    });
  });

  it('should have non-negative unit cost', () => {
    assertProperty(partArb, (part) => {
      expect(part.unitCost).toBeGreaterThanOrEqual(0);
    });
  });

  it('should have valid source', () => {
    assertProperty(partArb, (part) => {
      expect([PartSource.INVENTORY, PartSource.ORDERED, PartSource.CUSTOMER_SUPPLIED]).toContain(part.source);
    });
  });
});

describe('ConversationContext Properties', () => {
  it('should have intent confidence between 0 and 1', () => {
    assertProperty(conversationContextArb, (context) => {
      if (context.currentIntent) {
        expect(context.currentIntent.confidence).toBeGreaterThanOrEqual(0);
        expect(context.currentIntent.confidence).toBeLessThanOrEqual(1);
      }
    });
  });

  it('should have entity confidence between 0 and 1', () => {
    assertProperty(conversationContextArb, (context) => {
      context.entities.forEach((entity) => {
        expect(entity.confidence).toBeGreaterThanOrEqual(0);
        expect(entity.confidence).toBeLessThanOrEqual(1);
      });
    });
  });

  it('should have entity span with start < end', () => {
    assertProperty(conversationContextArb, (context) => {
      context.entities.forEach((entity) => {
        expect(entity.span[0]).toBeLessThan(entity.span[1]);
      });
    });
  });

  it('should have chronologically ordered history', () => {
    assertProperty(conversationContextArb, (context) => {
      if (context.history.length > 1) {
        for (let i = 0; i < context.history.length - 1; i++) {
          expect(context.history[i].timestamp.getTime()).toBeLessThanOrEqual(
            context.history[i + 1].timestamp.getTime()
          );
        }
      }
    });
  });
});

describe('Schedule Properties', () => {
  it('should have utilization rate between 0 and 1', () => {
    assertProperty(scheduleArb, (schedule) => {
      expect(schedule.utilizationRate).toBeGreaterThanOrEqual(0);
      expect(schedule.utilizationRate).toBeLessThanOrEqual(1);
    });
  });

  it('should have positive estimated completion time', () => {
    assertProperty(scheduleArb, (schedule) => {
      expect(schedule.estimatedCompletionTime).toBeGreaterThan(0);
    });
  });

  it('should have non-negative route distances', () => {
    assertProperty(scheduleArb, (schedule) => {
      schedule.routes.forEach((route) => {
        expect(route.totalDistance).toBeGreaterThanOrEqual(0);
      });
    });
  });

  it('should have positive route durations', () => {
    assertProperty(scheduleArb, (schedule) => {
      schedule.routes.forEach((route) => {
        expect(route.totalDuration).toBeGreaterThan(0);
      });
    });
  });
});

describe('MCPToolCall Properties', () => {
  it('should have non-negative duration', () => {
    assertProperty(mcpToolCallArb, (toolCall) => {
      expect(toolCall.duration).toBeGreaterThanOrEqual(0);
    });
  });

  it('should have valid server ID', () => {
    assertProperty(mcpToolCallArb, (toolCall) => {
      expect(['filesystem', 'database', 'inventree', 'partdb', 'kicost']).toContain(toolCall.serverId);
    });
  });

  it('should have valid agent ID', () => {
    assertProperty(mcpToolCallArb, (toolCall) => {
      expect(['intake', 'diagnostic', 'fulfillment']).toContain(toolCall.agentId);
    });
  });
});

describe('TriageResult Properties', () => {
  it('should have confidence between 0 and 1', () => {
    assertProperty(triageResultArb, (triage) => {
      expect(triage.confidence).toBeGreaterThanOrEqual(0);
      expect(triage.confidence).toBeLessThanOrEqual(1);
    });
  });

  it('should have priority between 1 and 10', () => {
    assertProperty(triageResultArb, (triage) => {
      expect(triage.priority).toBeGreaterThanOrEqual(1);
      expect(triage.priority).toBeLessThanOrEqual(10);
    });
  });

  it('should have positive estimated duration', () => {
    assertProperty(triageResultArb, (triage) => {
      expect(triage.estimatedDuration).toBeGreaterThan(0);
    });
  });

  it('should have at least one required skill', () => {
    assertProperty(triageResultArb, (triage) => {
      expect(triage.requiredSkills.length).toBeGreaterThan(0);
    });
  });

  it('should have at least one suggested technician', () => {
    assertProperty(triageResultArb, (triage) => {
      expect(triage.suggestedTechnicians.length).toBeGreaterThan(0);
    });
  });
});

// Performance test to verify 1000+ runs complete in reasonable time
describe('Performance Tests', () => {
  it('should complete 1000 lead property tests in reasonable time', () => {
    const startTime = Date.now();
    
    fc.assert(
      fc.property(leadArb, (lead) => {
        expect(lead.urgency).toBeDefined();
      }),
      getPropertyTestConfig('default')
    );
    
    const duration = Date.now() - startTime;
    console.log(`Completed 1000 lead property tests in ${duration}ms`);
    
    // Should complete in less than 10 seconds
    expect(duration).toBeLessThan(10000);
  });
});
