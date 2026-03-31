/**
 * System Tests for MCP Client
 * 
 * Tests MCP throughput (1000+ calls/minute), concurrent execution,
 * performance, and memory usage.
 * 
 * **Validates: Requirements 10.6, 10.9, 14.9, 14.10**
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { MCPClient } from './client';
import { MCPConnection } from './connection';
import {
  MCPConnectionConfig,
  MCPConnectionStatus,
  MCPToolSchema,
} from './types';

// ============================================================================
// Mock MCP Connection for System Tests
// ============================================================================

class MockMCPConnection extends MCPConnection {
  private mockToolSchemas: Map<string, MCPToolSchema> = new Map();
  private mockResponses: Map<string, any> = new Map();
  private callCount: number = 0;
  private executionDelay: number = 0;

  constructor(config: MCPConnectionConfig) {
    super(config);
  }

  async connect(): Promise<void> {
    // Mock connection
  }

  async disconnect(): Promise<void> {
    // Mock disconnection
  }

  getState() {
    return {
      serverName: (this as any).config.serverName,
      status: MCPConnectionStatus.CONNECTED,
      connectedAt: new Date(),
      toolSchemas: this.mockToolSchemas,
    };
  }

  getToolSchema(toolName: string): MCPToolSchema | undefined {
    return this.mockToolSchemas.get(toolName);
  }

  getAllToolSchemas(): MCPToolSchema[] {
    return Array.from(this.mockToolSchemas.values());
  }

  setMockToolSchema(schema: MCPToolSchema): void {
    this.mockToolSchemas.set(schema.name, schema);
  }

  setMockResponse(toolName: string, response: any): void {
    this.mockResponses.set(toolName, response);
  }

  setExecutionDelay(delay: number): void {
    this.executionDelay = delay;
  }

  getCallCount(): number {
    return this.callCount;
  }

  resetCallCount(): void {
    this.callCount = 0;
  }

  async sendRequest(method: string, params: any): Promise<any> {
    if (method === 'tools/execute') {
      this.callCount++;

      // Simulate execution delay
      if (this.executionDelay > 0) {
        await new Promise((resolve) => setTimeout(resolve, this.executionDelay));
      }

      const toolName = params.name;
      const response = this.mockResponses.get(toolName);
      if (response !== undefined) {
        return response;
      }
      return { success: true, result: `result-${this.callCount}` };
    }
    return {};
  }
}

// ============================================================================
// System Test 1: MCP Throughput (1000+ calls/minute)
// **Validates: Requirement 14.9**
// ============================================================================

describe('System Test 1: MCP Throughput', () => {
  let client: MCPClient;

  beforeEach(() => {
    client = new MCPClient({
      enableCaching: false, // Disable caching to test actual throughput
      enableRetry: false,
    });
  });

  afterEach(async () => {
    await client.disconnectAll();
  });

  it('should handle 1000+ tool calls per minute', async () => {
    const mockConnection = new MockMCPConnection({
      serverName: 'test-server',
      transport: 'stdio',
    });

    mockConnection.setMockToolSchema({
      name: 'fast_tool',
      description: 'Fast tool for throughput testing',
      parameters: [{ name: 'id', type: 'string', required: true }],
    });
    mockConnection.setExecutionDelay(1); // 1ms per call

    (client as any).connections.set('test-server', mockConnection);

    const targetCalls = 1000;
    const startTime = Date.now();

    // Execute 1000 calls sequentially
    const promises = [];
    for (let i = 0; i < targetCalls; i++) {
      promises.push(
        client.executeTool('test-server', {
          toolName: 'fast_tool',
          arguments: { id: String(i) },
        })
      );
    }

    const results = await Promise.all(promises);
    const duration = Date.now() - startTime;
    const callsPerMinute = (targetCalls / duration) * 60000;

    console.log(`Throughput: ${callsPerMinute.toFixed(0)} calls/minute`);
    console.log(`Duration: ${duration}ms for ${targetCalls} calls`);

    // Verify all calls succeeded
    const successCount = results.filter((r) => r.success).length;
    expect(successCount).toBe(targetCalls);

    // Verify throughput meets requirement (1000+ calls/minute)
    expect(callsPerMinute).toBeGreaterThanOrEqual(1000);
  }, 120000); // 2 minute timeout

  it('should maintain throughput with caching enabled', async () => {
    const cachedClient = new MCPClient({
      enableCaching: true,
      enableRetry: false,
    });

    const mockConnection = new MockMCPConnection({
      serverName: 'test-server',
      transport: 'stdio',
    });

    mockConnection.setMockToolSchema({
      name: 'cached_tool',
      description: 'Tool for cache throughput testing',
      parameters: [{ name: 'id', type: 'string', required: true }],
    });
    mockConnection.setExecutionDelay(5); // 5ms per actual call

    (cachedClient as any).connections.set('test-server', mockConnection);

    const uniqueIds = 100; // Only 100 unique IDs
    
    // First, populate the cache with 100 unique calls
    const populatePromises = [];
    for (let i = 0; i < uniqueIds; i++) {
      populatePromises.push(
        cachedClient.executeTool('test-server', {
          toolName: 'cached_tool',
          arguments: { id: String(i) },
        })
      );
    }
    await Promise.all(populatePromises);
    
    const initialCallCount = mockConnection.getCallCount();
    console.log(`Initial cache population: ${initialCallCount} calls`);
    
    // Now execute 2000 calls that should all hit the cache
    const targetCalls = 2000;
    const startTime = Date.now();
    
    const promises = [];
    for (let i = 0; i < targetCalls; i++) {
      const id = String(i % uniqueIds);
      promises.push(
        cachedClient.executeTool('test-server', {
          toolName: 'cached_tool',
          arguments: { id },
        })
      );
    }

    const results = await Promise.all(promises);
    const duration = Date.now() - startTime;
    const callsPerMinute = (targetCalls / duration) * 60000;

    console.log(`Cached throughput: ${callsPerMinute.toFixed(0)} calls/minute`);
    console.log(`Duration: ${duration}ms for ${targetCalls} calls`);
    console.log(`Actual server calls after cache: ${mockConnection.getCallCount() - initialCallCount}`);

    // Verify all calls succeeded
    const successCount = results.filter((r) => r.success).length;
    expect(successCount).toBe(targetCalls);

    // Verify no additional server calls were made (all from cache)
    expect(mockConnection.getCallCount() - initialCallCount).toBe(0);

    // Verify throughput is much higher with caching
    expect(callsPerMinute).toBeGreaterThanOrEqual(5000);

    await cachedClient.disconnectAll();
  }, 120000);
});

// ============================================================================
// System Test 2: Concurrent Tool Execution
// **Validates: Requirements 10.6, 14.9**
// ============================================================================

describe('System Test 2: Concurrent Tool Execution', () => {
  let client: MCPClient;

  beforeEach(() => {
    client = new MCPClient({
      enableCaching: false,
      enableRetry: false,
      maxConnections: 10,
    });
  });

  afterEach(async () => {
    await client.disconnectAll();
  });

  it('should handle 100+ concurrent tool executions', async () => {
    const mockConnection = new MockMCPConnection({
      serverName: 'test-server',
      transport: 'stdio',
    });

    mockConnection.setMockToolSchema({
      name: 'concurrent_tool',
      description: 'Tool for concurrency testing',
      parameters: [{ name: 'id', type: 'string', required: true }],
    });
    mockConnection.setExecutionDelay(10); // 10ms per call

    (client as any).connections.set('test-server', mockConnection);

    const concurrentCalls = 100;
    const startTime = Date.now();

    // Execute 100 calls concurrently
    const promises = Array.from({ length: concurrentCalls }, (_, i) =>
      client.executeTool('test-server', {
        toolName: 'concurrent_tool',
        arguments: { id: String(i) },
      })
    );

    const results = await Promise.all(promises);
    const duration = Date.now() - startTime;

    console.log(`Concurrent execution: ${duration}ms for ${concurrentCalls} calls`);
    console.log(`Average latency: ${(duration / concurrentCalls).toFixed(2)}ms`);

    // Verify all calls succeeded
    const successCount = results.filter((r) => r.success).length;
    expect(successCount).toBe(concurrentCalls);

    // Verify concurrent execution is faster than sequential
    // Sequential would take at least concurrentCalls * executionDelay = 1000ms
    // Concurrent should be much faster
    expect(duration).toBeLessThan(500);
  });

  it('should handle concurrent calls across multiple servers', async () => {
    const serverCount = 5;
    const callsPerServer = 20;

    // Setup multiple mock connections
    for (let i = 0; i < serverCount; i++) {
      const mockConnection = new MockMCPConnection({
        serverName: `server-${i}`,
        transport: 'stdio',
      });

      mockConnection.setMockToolSchema({
        name: 'multi_server_tool',
        description: 'Tool for multi-server testing',
        parameters: [{ name: 'id', type: 'string', required: true }],
      });
      mockConnection.setExecutionDelay(5);

      (client as any).connections.set(`server-${i}`, mockConnection);
    }

    const startTime = Date.now();

    // Execute calls across all servers concurrently
    const promises = [];
    for (let i = 0; i < serverCount; i++) {
      for (let j = 0; j < callsPerServer; j++) {
        promises.push(
          client.executeTool(`server-${i}`, {
            toolName: 'multi_server_tool',
            arguments: { id: `${i}-${j}` },
          })
        );
      }
    }

    const results = await Promise.all(promises);
    const duration = Date.now() - startTime;
    const totalCalls = serverCount * callsPerServer;

    console.log(`Multi-server execution: ${duration}ms for ${totalCalls} calls`);

    // Verify all calls succeeded
    const successCount = results.filter((r) => r.success).length;
    expect(successCount).toBe(totalCalls);
  });
});

// ============================================================================
// System Test 3: Performance Under Load
// **Validates: Requirements 14.9, 14.10**
// ============================================================================

describe('System Test 3: Performance Under Load', () => {
  let client: MCPClient;

  beforeEach(() => {
    client = new MCPClient({
      enableCaching: true,
      enableRetry: true,
      defaultRetryPolicy: {
        maxRetries: 2,
        initialDelay: 50,
        maxDelay: 500,
        exponentialBackoff: true,
      },
    });
  });

  afterEach(async () => {
    await client.disconnectAll();
  });

  it('should maintain 99.5%+ success rate under load', async () => {
    const mockConnection = new MockMCPConnection({
      serverName: 'test-server',
      transport: 'stdio',
    });

    mockConnection.setMockToolSchema({
      name: 'load_test_tool',
      description: 'Tool for load testing',
      parameters: [{ name: 'id', type: 'string', required: true }],
    });
    mockConnection.setExecutionDelay(2);

    (client as any).connections.set('test-server', mockConnection);

    const totalCalls = 1000;
    const startTime = Date.now();

    // Execute 1000 calls
    const promises = Array.from({ length: totalCalls }, (_, i) =>
      client.executeTool('test-server', {
        toolName: 'load_test_tool',
        arguments: { id: String(i) },
      })
    );

    const results = await Promise.all(promises);
    const duration = Date.now() - startTime;

    const successCount = results.filter((r) => r.success).length;
    const successRate = (successCount / totalCalls) * 100;

    console.log(`Success rate: ${successRate.toFixed(2)}%`);
    console.log(`Duration: ${duration}ms for ${totalCalls} calls`);
    console.log(`Average latency: ${(duration / totalCalls).toFixed(2)}ms`);

    // Verify success rate meets requirement (99.5%+)
    expect(successRate).toBeGreaterThanOrEqual(99.5);
  }, 120000);

  it('should handle large result sets efficiently', async () => {
    const mockConnection = new MockMCPConnection({
      serverName: 'test-server',
      transport: 'stdio',
    });

    mockConnection.setMockToolSchema({
      name: 'large_result_tool',
      description: 'Tool that returns large results',
      parameters: [],
    });

    // Create a large result set (1000 items)
    const largeResult = {
      items: Array.from({ length: 1000 }, (_, i) => ({
        id: i,
        name: `Item ${i}`,
        description: `Description for item ${i}`,
        metadata: {
          created: new Date().toISOString(),
          updated: new Date().toISOString(),
        },
      })),
    };

    mockConnection.setMockResponse('large_result_tool', largeResult);
    (client as any).connections.set('test-server', mockConnection);

    const startTime = Date.now();
    const result = await client.executeTool('test-server', {
      toolName: 'large_result_tool',
      arguments: {},
    });
    const duration = Date.now() - startTime;

    console.log(`Large result processing: ${duration}ms`);
    console.log(`Result size: ${JSON.stringify(result.result).length} bytes`);

    expect(result.success).toBe(true);
    expect(result.result.items).toHaveLength(1000);

    // Verify processing is efficient (< 100ms)
    expect(duration).toBeLessThan(100);
  });
});

// ============================================================================
// System Test 4: Memory Usage and Connection Pooling
// **Validates: Requirements 10.6, 10.9**
// ============================================================================

describe('System Test 4: Memory Usage and Connection Pooling', () => {
  it('should enforce maximum connection limit', async () => {
    const client = new MCPClient({
      maxConnections: 5,
      enableCaching: false,
      enableRetry: false,
    });

    // Add 5 connections (should succeed)
    for (let i = 0; i < 5; i++) {
      const mockConnection = new MockMCPConnection({
        serverName: `server-${i}`,
        transport: 'stdio',
      });
      (client as any).connections.set(`server-${i}`, mockConnection);
    }

    expect(client.getAllConnections()).toHaveLength(5);

    // Try to add 6th connection (should fail)
    const mockConnection = new MockMCPConnection({
      serverName: 'server-6',
      transport: 'stdio',
    });

    await expect(
      client.addConnection({
        serverName: 'server-6',
        transport: 'stdio',
      })
    ).rejects.toThrow('Maximum connections reached');

    await client.disconnectAll();
  });

  it('should cleanup cache efficiently', async () => {
    const client = new MCPClient({
      enableCaching: true,
      cacheTTL: 100, // 100ms TTL for fast expiration
      enableRetry: false,
    });

    const mockConnection = new MockMCPConnection({
      serverName: 'test-server',
      transport: 'stdio',
    });

    mockConnection.setMockToolSchema({
      name: 'cache_test_tool',
      description: 'Tool for cache testing',
      parameters: [{ name: 'id', type: 'string', required: true }],
    });

    (client as any).connections.set('test-server', mockConnection);

    // Create 100 cached entries
    const promises = Array.from({ length: 100 }, (_, i) =>
      client.executeTool('test-server', {
        toolName: 'cache_test_tool',
        arguments: { id: String(i) },
      })
    );

    await Promise.all(promises);

    // Check cache size
    const statsBefore = client.getCacheStats();
    expect(statsBefore.size).toBe(100);

    // Wait for cache to expire
    await new Promise((resolve) => setTimeout(resolve, 150));

    // Cleanup expired entries
    const removed = client.cleanupCache();
    console.log(`Cleaned up ${removed} expired cache entries`);

    const statsAfter = client.getCacheStats();
    expect(statsAfter.size).toBe(0);
    expect(removed).toBe(100);

    await client.disconnectAll();
  });

  it('should handle connection lifecycle correctly', async () => {
    const client = new MCPClient({
      enableCaching: false,
      enableRetry: false,
    });

    // Add connection
    const mockConnection = new MockMCPConnection({
      serverName: 'test-server',
      transport: 'stdio',
    });
    (client as any).connections.set('test-server', mockConnection);

    expect(client.getAllConnections()).toHaveLength(1);

    // Get connection status
    const status = client.getConnectionStatus();
    expect(status).toHaveLength(1);
    expect(status[0].serverName).toBe('test-server');
    expect(status[0].status).toBe(MCPConnectionStatus.CONNECTED);

    // Remove connection
    await client.removeConnection('test-server');
    expect(client.getAllConnections()).toHaveLength(0);

    // Try to get removed connection
    const connection = client.getConnection('test-server');
    expect(connection).toBeUndefined();

    await client.disconnectAll();
  });
});

// ============================================================================
// System Test 5: End-to-End Performance Validation
// **Validates: Requirements 14.9, 14.10**
// ============================================================================

describe('System Test 5: End-to-End Performance Validation', () => {
  it('should meet all performance requirements', async () => {
    const client = new MCPClient({
      enableCaching: true,
      enableRetry: true,
      defaultRetryPolicy: {
        maxRetries: 3,
        initialDelay: 100,
        maxDelay: 1000,
        exponentialBackoff: true,
      },
    });

    const mockConnection = new MockMCPConnection({
      serverName: 'test-server',
      transport: 'stdio',
    });

    mockConnection.setMockToolSchema({
      name: 'performance_tool',
      description: 'Tool for performance validation',
      parameters: [{ name: 'id', type: 'string', required: true }],
    });
    mockConnection.setExecutionDelay(1);

    (client as any).connections.set('test-server', mockConnection);

    // Test 1: Throughput (1000+ calls/minute)
    console.log('Testing throughput...');
    const throughputStart = Date.now();
    const throughputPromises = Array.from({ length: 1000 }, (_, i) =>
      client.executeTool('test-server', {
        toolName: 'performance_tool',
        arguments: { id: String(i) },
      })
    );
    await Promise.all(throughputPromises);
    const throughputDuration = Date.now() - throughputStart;
    const callsPerMinute = (1000 / throughputDuration) * 60000;
    console.log(`  Throughput: ${callsPerMinute.toFixed(0)} calls/minute`);
    expect(callsPerMinute).toBeGreaterThanOrEqual(1000);

    // Test 2: Success rate (99.5%+)
    console.log('Testing success rate...');
    const successResults = await Promise.all(throughputPromises);
    const successRate =
      (successResults.filter((r) => r.success).length / 1000) * 100;
    console.log(`  Success rate: ${successRate.toFixed(2)}%`);
    expect(successRate).toBeGreaterThanOrEqual(99.5);

    // Test 3: Cache effectiveness
    console.log('Testing cache effectiveness...');
    mockConnection.resetCallCount();
    const cachePromises = Array.from({ length: 100 }, (_, i) =>
      client.executeTool('test-server', {
        toolName: 'performance_tool',
        arguments: { id: String(i % 10) }, // Only 10 unique IDs
      })
    );
    await Promise.all(cachePromises);
    const actualCalls = mockConnection.getCallCount();
    console.log(`  Actual server calls: ${actualCalls} (out of 100 requests)`);
    expect(actualCalls).toBeLessThanOrEqual(10);

    await client.disconnectAll();
  }, 120000);
});
